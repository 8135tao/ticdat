import sys
import unittest
import ticdat._private.utils as utils



_GRB_INFINITY = 1e+100

#uncomment decorator to drop into debugger for assertTrue, assertFalse failures
@utils.failToDebugger
class TestUtils(unittest.TestCase):

    def _origDietTicDat(self):
        # this is the gurobi diet data in ticDat format

        class _(object) :
            pass

        dat = _() # simplest object with a __dict__

        dat.categories = {
          'calories': {"minNutrition": 1800, "maxNutrition" : 2200},
          'protein':  {"minNutrition": 91,   "maxNutrition" : _GRB_INFINITY},
          'fat':      {"minNutrition": 0,    "maxNutrition" : 65},
          'sodium':   {"minNutrition": 0,    "maxNutrition" : 1779}}

        dat.foods = {
          'hamburger': {"cost": 2.49},
          'chicken':   {"cost": 2.89},
          'hot dog':   {"cost": 1.50},
          'fries':     {"cost": 1.89},
          'macaroni':  {"cost": 2.09},
          'pizza':     {"cost": 1.99},
          'salad':     {"cost": 2.49},
          'milk':      {"cost": 0.89},
          'ice cream': {"cost": 1.59}}

        dat.nutritionQuantities = {
          ('hamburger', 'calories'): {"qty" : 410},
          ('hamburger', 'protein'):  {"qty" : 24},
          ('hamburger', 'fat'):      {"qty" : 26},
          ('hamburger', 'sodium'):   {"qty" : 730},
          ('chicken',   'calories'): {"qty" : 420},
          ('chicken',   'protein'):  {"qty" : 32},
          ('chicken',   'fat'):      {"qty" : 10},
          ('chicken',   'sodium'):   {"qty" : 1190},
          ('hot dog',   'calories'): {"qty" : 560},
          ('hot dog',   'protein'):  {"qty" : 20},
          ('hot dog',   'fat'):      {"qty" : 32},
          ('hot dog',   'sodium'):   {"qty" : 1800},
          ('fries',     'calories'): {"qty" : 380},
          ('fries',     'protein'):  {"qty" : 4},
          ('fries',     'fat'):      {"qty" : 19},
          ('fries',     'sodium'):   {"qty" : 270},
          ('macaroni',  'calories'): {"qty" : 320},
          ('macaroni',  'protein'):  {"qty" : 12},
          ('macaroni',  'fat'):      {"qty" : 10},
          ('macaroni',  'sodium'):   {"qty" : 930},
          ('pizza',     'calories'): {"qty" : 320},
          ('pizza',     'protein'):  {"qty" : 15},
          ('pizza',     'fat'):      {"qty" : 12},
          ('pizza',     'sodium'):   {"qty" : 820},
          ('salad',     'calories'): {"qty" : 320},
          ('salad',     'protein'):  {"qty" : 31},
          ('salad',     'fat'):      {"qty" : 12},
          ('salad',     'sodium'):   {"qty" : 1230},
          ('milk',      'calories'): {"qty" : 100},
          ('milk',      'protein'):  {"qty" : 8},
          ('milk',      'fat'):      {"qty" : 2.5},
          ('milk',      'sodium'):   {"qty" : 125},
          ('ice cream', 'calories'): {"qty" : 330},
          ('ice cream', 'protein'):  {"qty" : 8},
          ('ice cream', 'fat'):      {"qty" : 10},
          ('ice cream', 'sodium'):   {"qty" : 180} }

        return dat

    def testOne(self):
        objGood = utils.goodTicDatObject
        dataDict = self._origDietTicDat()
        self.assertTrue(objGood(dataDict) and objGood(dataDict, ("categories", "foods", "nutritionQuantities")))
        msg = []
        dataDict.foods[("milk", "cookies")] = {"cost": float("inf")}
        dataDict.boger = []
        self.assertFalse(objGood(dataDict) or objGood(dataDict, badMessageHolder= msg))
        self.assertTrue({"foods : Inconsistent key lengths", "boger : Not a dict-like object."} == set(msg))
        self.assertTrue(objGood(dataDict, ("categories", "nutritionQuantities")))

        dataDict = self._origDietTicDat()
        dataDict.categories["boger"] = {"cost":1}
        dataDict.categories["boger"] = {"cost":1}
        self.assertFalse(objGood(dataDict) or objGood(dataDict, badMessageHolder= msg))
        self.assertTrue({"foods : Inconsistent key lengths", "boger : Not a dict-like object.",
                         'categories : Inconsistent field name keys.'} == set(msg))


def runTheTests(fastOnly=True) :
    utils.runSuite(TestUtils, fastOnly=fastOnly)

# Run the tests.
if __name__ == "__main__":
    runTheTests()

