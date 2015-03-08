
# !!! KNOWN BUGS !!!!
# -> For xls file writing, None not being written out as NULL. Not sure how xlwd, xlwt is supposed to handle this?
# -> For csv file reading, all data is turned into floats if possible. So zip codes will be turned into floats
# !!! REMEMBER !!!! ticDat is supposed to facilitate rapid prototyping and port-ready solver engine
#                   development. The true fix for these cosmetic flaws is to use the Opalytics platform
#                   for industrial data and the ticDat library for cleaner, isolated development/testing.

import utils as utils
from utils import verify, freezableFactory, FrozenDict, FreezeableDict,  dictish, containerish
import collections as clt
import xls
import csvtd as csv

def _keyLen(k) :
    if not utils.containerish(k) :
        return 1
    try:
        rtn = len(k)
    except :
        rtn = 0
    return rtn


class TicDatFactory(freezableFactory(object, "_isFrozen")) :
    """
    Primary class for ticDat library. This class is constructed with a schema (a listing of the primary key
    fields and data fields for each table). Client code can then read/write ticDat objects from a variety of data
    sources. Analytical code that that reads/writes from ticDat objects can then be used, without change,
    on different data sources, or on the Opalytics platform.
    """
    def __init__(self, primaryKeyFields = {}, dataFields = {}, generatorTables = (), foreignKeys = {},
                 defaultValues = {}):
        primaryKeyFields, dataFields = utils.checkSchema(primaryKeyFields, dataFields)
        self.primaryKeyFields, self.dataFields = primaryKeyFields, dataFields
        self.allTables = frozenset(set(self.primaryKeyFields).union(self.dataFields))
        verify(containerish(generatorTables) and set(generatorTables).issubset(self.allTables),
               "generatorTables should be a container of table names")
        verify(not any(primaryKeyFields.get(t) for t in generatorTables),
               "Can not make generators from tables with primary keys")
        verify(dictish(foreignKeys) and set(foreignKeys).issubset(self.allTables) and
               all (containerish(_) for _ in foreignKeys.values()),
               "foreignKeys needs to a dictionary mapping table names to containers of foreign key definitions")
        for t,l in foreignKeys.items() :
            msg = []
            if not all(self._goodForeignKey(t, fk, msg.append) for fk in l) :
                raise utils.TicDatError("Bad foreign key for %s : %s"%(t, ",".join(msg)))
        self.foreignKeys = utils.deepFreezeContainer(foreignKeys)

        verify(dictish(defaultValues) and set(defaultValues).issubset(self.allTables),
               "default values needs to be a dictionary keyed by table names")
        for t,d in defaultValues.items():
            verify(dictish(d) and set(d).issubset(self._allFields(t)),
                   "The default values for table %s is not a dictionary keyed by field names"%t)
        self.defaultValues = utils.deepFreezeContainer(defaultValues)
        dataRowFactory = FrozenDict({t : utils.ticDataRowFactory(t,
                self.primaryKeyFields.get(t, ()), self.dataFields.get(t, ()),
                defaultValues=  {k:v for k,v in self.defaultValues.get(t, {}).items()
                    if k in self.dataFields.get(t, ())}) for t in self.allTables})
        self.generatorTables = frozenset(generatorTables)
        goodTicDatTable = self.goodTicDatTable
        superSelf = self
        def ticDatTableFactory(allDataDicts, tableName, primaryKey = (), rowFactory = None) :
            assert containerish(primaryKey)
            primaryKey = primaryKey or  self.primaryKeyFields.get(tableName, ())
            keyLen = len(primaryKey)
            rowFactory = rowFactory or dataRowFactory[tableName]
            if keyLen > 0 :
                class TicDatDict (FreezeableDict) :
                    def __init__(self, *_args, **_kwargs):
                        super(TicDatDict, self).__init__(*_args, **_kwargs)
                        allDataDicts.append(self)
                    def __setitem__(self, key, value):
                        verify(containerish(key) ==  (keyLen > 1) and (keyLen == 1 or keyLen == len(key)),
                               "inconsistent key length for %s"%tableName)
                        return super(TicDatDict, self).__setitem__(key, rowFactory(value))
                    def __getitem__(self, item):
                        if item not in self and rowFactory is dataRowFactory.get(tableName):
                            self[item] = rowFactory({})
                        return super(TicDatDict, self).__getitem__(item)
                assert dictish(TicDatDict)
                return TicDatDict
            class TicDatDataList(clt.MutableSequence):
                def __init__(self, *_args):
                    self._list = list()
                    self.extend(list(_args))
                def __len__(self): return len(self._list)
                def __getitem__(self, i): return self._list[i]
                def __delitem__(self, i): del self._list[i]
                def __setitem__(self, i, v):
                    self._list[i] = rowFactory(v)
                def insert(self, i, v):
                    self._list.insert(i, rowFactory(v))
                def __repr__(self):
                    return "td:" + self._list.__repr__()
            assert containerish(TicDatDataList) and not dictish(TicDatDataList)
            return TicDatDataList
        def generatorFactory(data, tableName) :
            assert tableName in self.generatorTables
            def generatorFunction() :
                for row in (data if containerish(data) else data()):
                    yield dataRowFactory[tableName](row)
            return generatorFunction
        class _TicDat(utils.freezableFactory(object, "_isFrozen")) :
            def _freeze(self):
                if getattr(self, "_isFrozen", False) :
                    return
                for t in superSelf.allTables :
                    _t = getattr(self, t)
                    if utils.dictish(_t) or utils.containerish(_t) :
                        for v in getattr(_t, "values", lambda : _t)() :
                            if not getattr(v, "_dataFrozen", False) :
                                v._dataFrozen =True
                                v._attributesFrozen = True
                            else : # we freeze the data-less ones off the bat as empties, easiest way
                                assert (len(v) == 0) and v._attributesFrozen
                        if utils.dictish(_t) :
                            _t._dataFrozen  = True
                            _t._attributesFrozen = True
                        elif utils.containerish(_t) :
                            setattr(self, t, tuple(_t))
                    else :
                        assert callable(_t) and t in superSelf.generatorTables
                for _t in getattr(self, "_allDataDicts", ()) :
                    if utils.dictish(_t) and not getattr(_t, "_attributesFrozen", False) :
                        _t._dataFrozen  = True
                        _t._attributesFrozen = True
                self._isFrozen = True
            def __repr__(self):
                return "td:" + tuple(superSelf.allTables).__repr__()
        class TicDat(_TicDat) :
            def __init__(self, **initTables):
                self._allDataDicts = []
                for t in initTables :
                    verify(t in superSelf.allTables, "Unexpected table name %s"%t)
                for t,v in initTables.items():
                    badTicDatTable = []
                    if not (goodTicDatTable(v, t, lambda x : badTicDatTable.append(x))) :
                        raise utils.TicDatError(t + " cannot be treated as a ticDat table : " + badTicDatTable[-1])
                    if superSelf.primaryKeyFields.get(t) :
                     for _k in v :
                        verify((hasattr(_k, "__len__") and (len(_k) == len(primaryKeyFields.get(t, ())) > 1) or
                               len(primaryKeyFields.get(t, ())) == 1),
                           "Unexpected number of primary key fields for %s"%t)
                     # lots of verification inside the dataRowFactory
                     setattr(self, t, ticDatTableFactory(self._allDataDicts, t)({_k : dataRowFactory[t](v[_k]
                                                            if utils.dictish(v) else ()) for _k in v}))
                    elif t in superSelf.generatorTables :
                        setattr(self, t, generatorFactory(v, t))
                    else :
                        setattr(self, t, ticDatTableFactory(self._allDataDicts, t)(*v))
                for t in set(superSelf.allTables).difference(initTables) :
                    setattr(self, t, ticDatTableFactory(self._allDataDicts, t)())
                canLinkWithMe = lambda t : t not in generatorTables and superSelf.primaryKeyFields.get(t)
                for t, fks in superSelf.foreignKeys.items() :
                  if canLinkWithMe(t):
                    lens = {z:len([x for x in fks if x["foreignTable"] == z]) for z in [y["foreignTable"] for y in fks]}
                    for fk in fks:
                      if canLinkWithMe(fk["foreignTable"])  :
                        linkName = t if lens[fk["foreignTable"]] ==1 else (t + "_" + "_".join(fk["mappings"].keys()))
                        if linkName not in ("keys", "items", "values") :
                            ft = getattr(self, fk["foreignTable"])
                            foreignPrimaryKey = superSelf.primaryKeyFields[fk["foreignTable"]]
                            localPrimaryKey = superSelf.primaryKeyFields[t]
                            assert all(pk for pk in (foreignPrimaryKey, localPrimaryKey))
                            assert set(foreignPrimaryKey) == set(fk["mappings"].values())
                            appendageForeignKey = (
                                            set(foreignPrimaryKey) == set(fk["mappings"].values()) and
                                            set(localPrimaryKey) == set(fk["mappings"].keys()))
                            reverseMapping  = {v:k for k,v in fk["mappings"].items()}
                            tableFields = superSelf.primaryKeyFields.get(t, ()) + superSelf.dataFields.get(t, ())
                            localPosition = {x:tableFields.index(reverseMapping[x]) for x in foreignPrimaryKey}
                            unusedLocalPositions = {i for i,_ in enumerate(tableFields) if i not in
                                                    localPosition.values()}
                            if not appendageForeignKey :
                                newPrimaryKey = tuple(x for x in localPrimaryKey if x not in fk["mappings"].keys())
                                newDataDict = ticDatTableFactory(self._allDataDicts, linkName,
                                                newPrimaryKey, lambda x : x)
                                for row in ft.values() :
                                    setattr(row, linkName, newDataDict())
                            for key,row in getattr(self, t).items() :
                                keyRow = ((key,) if not containerish(key) else key) + \
                                         tuple(row[x] for x in dataFields[t])
                                lookUp = tuple(keyRow[localPosition[x]] for x in foreignPrimaryKey)
                                linkRow = ft.get(lookUp[0] if len(lookUp) ==1 else lookUp, None)
                                if linkRow is not None :
                                    if  appendageForeignKey :
                                        # the attribute is simply a reference to the mapping table if such a reference exists
                                        assert not hasattr(linkRow, linkName)
                                        setattr(linkRow, linkName,row)
                                    else :
                                        _key = tuple(x for i,x in enumerate(keyRow[:-len(row)]) if i in unusedLocalPositions)
                                        getattr(linkRow, linkName)[_key[0] if len(_key) == 1 else _key] = row

        self.TicDat = TicDat
        class FrozenTicDat(TicDat) :
            def __init__(self, **initTables):
                super(FrozenTicDat, self).__init__(**initTables)
                self._freeze()
        self.FrozenTicDat = FrozenTicDat
        if xls.importWorked :
            self.xls = xls.XlsTicFactory(self)
        if csv.importWorked :
            self.csv = csv.CsvTicFactory(self)

        self._isFrozen = True

    def _allFields(self, table):
        assert table in self.allTables
        return set(self.primaryKeyFields.get(table, ())).union(self.dataFields.get(table, ()))
    def _goodForeignKey(self, table, fk, badMessageHandler = lambda x : None):
        assert table in self.allTables
        if not self.primaryKeyFields.get(table) :
            badMessageHandler("%s has no primary keys and can't participate in a foreign key"%table)
            return True
        if not dictish(fk) :
            badMessageHandler("Not a dict")
            return False
        if set(fk.keys()) != {"foreignTable", "mappings"} :
            badMessageHandler("Unexpected keys")
            return False
        if fk["foreignTable"] not in self.allTables:
            badMessageHandler("Bad foreignTable value")
            return False
        if not self.primaryKeyFields.get(fk["foreignTable"]) :
            badMessageHandler("%s has no primary keys and can't participate in a foreign key"%fk["foreignTable"])
            return True
        if not dictish(fk["mappings"]) :
            badMessageHandler("mappings should refer to a dictionary")
            return False
        if not self._allFields(table).issuperset(fk["mappings"].keys()):
            badMessageHandler("the mappings dictionary should have keys in %s"%str(self._allFields(table)))
            return False
        if not set(self.primaryKeyFields[fk["foreignTable"]]) == set(fk["mappings"].values()):
            badMessageHandler("the mappings dictionary should have values that match the primary key of %s"%
                        fk["foreignTable"])
            return False
        
        return True

    def goodTicDatObject(self, dataObj, badMessageHandler = lambda x : None):
        """
        determines if an object can be can be converted to a TicDat data object.
        :param dataObj: the object to verify
        :param badMessageHandler: a call back function to receive description of any failure message
        :return: True if the dataObj can be converted to a TicDat data object. False otherwise.
        """
        rtn = True
        for t in self.allTables:
            if not hasattr(dataObj, t) :
                badMessageHandler(t + " not an attribute.")
                return False
            rtn = rtn and  self.goodTicDatTable(getattr(dataObj, t), t,
                    lambda x : badMessageHandler(t + " : " + x))
        return rtn

    def goodTicDatTable(self, dataTable, tableName, badMessageHandler = lambda x : None) :
        """
        determines if an object can be can be converted to a TicDat data table.
        :param dataObj: the object to verify
        :param tableName: the name of the table
        :param badMessageHandler: a call back function to receive description of any failure message
        :return: True if the dataObj can be converted to a TicDat data table. False otherwise.
        """
        if tableName not in self.allTables:
            badMessageHandler("%s is not a valid table name for this schema"%tableName)
            return False
        if tableName in self.generatorTables :
            assert not self.primaryKeyFields.get(tableName)
            verify((containerish(dataTable) or callable(dataTable)) and not dictish(dataTable),
                   "Expecting a container of rows or a generator function of rows for %s"%tableName)
            return self._goodDataRows(dataTable if containerish(dataTable) else dataTable(),
                                      tableName, badMessageHandler)
        if self.primaryKeyFields.get(tableName) :
            if utils.dictish(dataTable) :
                return self._goodTicDatDictTable(dataTable, tableName, badMessageHandler)
            if utils.containerish(dataTable):
                return  self._goodTicDatKeyContainer(dataTable, tableName, badMessageHandler)
        else :
            verify(utils.containerish(dataTable), "Unexpected ticDat table type for %s."%tableName)
            return self._goodDataRows(dataTable, tableName, badMessageHandler)
        badMessageHandler("Unexpected ticDat table type for %s."%tableName)
        return False


    def _goodTicDatKeyContainer(self, ticDatTable, tableName, badMessageHandler = lambda x : None) :
        assert containerish(ticDatTable) and not dictish(ticDatTable)
        if tableName in self.dataFields :
            badMessageHandler("%s contains data fields, and thus must be represented by a dict"%tableName)
            return False
        if not len(ticDatTable) :
            return True
        if not all(_keyLen(k) == len(self.primaryKeyFields[tableName])  for k in ticDatTable) :
            badMessageHandler("Inconsistent key lengths")
            return False
        return True
    def _goodTicDatDictTable(self, ticDatTable, tableName, badMessageHandler = lambda x : None):
        assert dictish(ticDatTable)
        if not len(ticDatTable) :
            return True
        if not all(_keyLen(k) == len(self.primaryKeyFields[tableName]) for k in ticDatTable.keys()) :
            badMessageHandler("Inconsistent key lengths")
            return False
        return self._goodDataRows(ticDatTable.values(), tableName, badMessageHandler)
    def _goodDataRows(self, dataRows, tableName, badMessageHandler = lambda x : None):
        dictishRows = tuple(x for x in dataRows if utils.dictish(x))
        if not all(set(x.keys()) == set(self.dataFields.get(tableName,())) for x in dictishRows) :
            badMessageHandler("Inconsistent data field name keys.")
            return False
        containerishRows = tuple(x for x in dataRows if utils.containerish(x) and not  utils.dictish(x))
        if not all(len(x) == len(self.dataFields.get(tableName,())) for x in containerishRows) :
            badMessageHandler("Inconsistent data row lengths.")
            return False
        singletonishRows = tuple(x for x in dataRows if not (utils.containerish(x) or utils.dictish(x)))
        if singletonishRows and (len(self.dataFields.get(tableName,())) != 1)  :
            badMessageHandler("Non-container data rows supported only for single-data-field tables")
            return False
        return True

    def _keyless(self, obj):
        assert self.goodTicDatObject(obj)
        class _ (object) :
            pass
        rtn = _()
        for t in self.allTables :
            _rtn = []
            _t = getattr(obj, t)
            if dictish(_t) :
                for pk, dr in _t.items() :
                    _rtn.append(dict(dr, **{_f: _pk for _f,_pk in
                                zip(self.primaryKeyFields[t], pk if containerish(pk) else (pk,))}))
            else :
                for dr in (_t if containerish(_t) else _t()) :
                    _rtn.append(dict(dr))
            setattr(rtn, t, _rtn)
        return rtn
    def _sameData(self, obj1, obj2):
        assert self.goodTicDatObject(obj1) and self.goodTicDatObject(obj2)
        def sameRow(r1, r2) :
            assert dictish(r1) and dictish(r2)
            if bool(r1) != bool(r2) or set(r1) != set(r2) :
                return False
            for _k in r1:
                if r1[_k] != r2[_k] :
                    return False
            return True
        for t in self.allTables :
            t1 = getattr(obj1, t)
            t2 = getattr(obj2, t)
            if dictish(t1) != dictish(t2) :
                return False
            if dictish(t1) :
                if set(t1) != set(t2) :
                    return False
                for k in t1 :
                    if not sameRow(t1[k], t2[k]) :
                        return False
            else :
                _iter = lambda x : x if containerish(x) else x()
                if not len(list(_iter(t1))) == len(list(_iter(t2))) :
                    return False
                for r1 in _iter(t1):
                    if not any (sameRow(r1, r2) for r2 in _iter(t2)) :
                        return False
        return True

def goodTicDatObject(ticDatObject, tableList = None, badMessageHandler = lambda x : None):
    """
    determines if an object qualifies as attribute collection of valid dict-of-dicts tibDat tables
    :param ticDatObject: the object to verify
    :param tableList: an optional list of attributes to verify. if missing, then all non calleable, non private,
                      attributes will be checked
    :param badMessageHandler: a call back function to receive description of any failure message
    :return: True if the ticDatObject is an attribute collection of valid dict-of-dicts. False otherwise.
    """
    if tableList is None :
        tableList = tuple(x for x in dir(ticDatObject) if not x.startswith("_") and
                          not callable(getattr(ticDatObject, x)))
    def _hasAttr(t) :
        if not hasattr(ticDatObject, t) :
            badMessageHandler(t + " not an attribute.")
            return False
        return True
    return all([_hasAttr(t) and goodTicDatTable(getattr(ticDatObject, t),
                lambda x : badMessageHandler(t + " : " + x)) for t in tableList])


def goodTicDatTable(ticDatTable, badMessageHandler = lambda x : None):
    """
    determines if a simple, dict-of-dicts qualifies as a valid ticDat table object
    :param ticDatTable: the object to verify
    :param badMessageHandler: a call back function to receive description of any failure message
    :return: True if the ticDatTable is a valid dict-of-dicts. False otherwise
    """
    if not (dictish(ticDatTable) or containerish(ticDatTable) or callable(ticDatTable)) :
        badMessageHandler("Unexpected object.")
        return False
    rows = ticDatTable.values() if dictish(ticDatTable) else (
           ticDatTable if containerish(ticDatTable) else tuple(ticDatTable()))
    if not rows :
        return True
    if dictish(ticDatTable) :
        def keyLen(k) :
            if not containerish(k) :
                return "singleton"
            try:
                rtn = len(k)
            except :
                rtn = 0
            return rtn
        if not all(keyLen(k) == keyLen(ticDatTable.keys()[0]) for k in ticDatTable.keys()) :
            badMessageHandler("Inconsistent key lengths")
            return False
    if not all(dictish(x) for x in rows) :
        badMessageHandler("At least one value is not a dict-like object")
        return False
    if not all(set(x.keys()) == set(rows[0].keys()) for x in rows) :
        badMessageHandler("Inconsistent field name keys.")
        return False
    return True

def freezeMe(x) :
    """
    Freezes a
    :param x: ticDat object
    :return: x, after it has been frozen
    """
    if not getattr(x, "_isFrozen", True) : #idempotent
        x._freeze()
    return x