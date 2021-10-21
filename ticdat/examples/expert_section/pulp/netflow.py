#
# Solve a multi-commodity flow problem as python package.
#
# Implement core functionality needed to achieve modularity.
# 1. Define the input data schema
# 2. Define the output data schema
# 3. Create a solve function that accepts a data set consistent with the input
#    schema and (if possible) returns a data set consistent with the output schema.
#
# Provides command line interface via ticdat.standard_main
# For example, typing
#   python netflow.py -i netflow_sample_data -o netflow_solution
# will read from the model stored in the netflow_sample_data directory
# and write the solution to a netflow_solution directory.  These data directories contain .csv files.
#
# This version of the netflow example takes extra precautions to avoid generating
# unneeded constraints. See the simplest_examples directory for a simpler version of this model.

# this version of the file uses pulp

import pulp
from ticdat import TicDatFactory, standard_main, Slicer

# ------------------------ define the input schema --------------------------------
input_schema = TicDatFactory (
    commodities=[["Name"], ["Volume"]],
    nodes=[["Name"], []],
    arcs=[["Source", "Destination"], ["Capacity"]],
    cost=[["Commodity", "Source", "Destination"], ["Cost"]],
    inflow=[["Commodity", "Node"], ["Quantity"]]
)

# Define the foreign key relationships
input_schema.add_foreign_key("arcs", "nodes", ['Source', 'Name'])
input_schema.add_foreign_key("arcs", "nodes", ['Destination', 'Name'])
input_schema.add_foreign_key("cost", "nodes", ['Source', 'Name'])
input_schema.add_foreign_key("cost", "nodes", ['Destination', 'Name'])
input_schema.add_foreign_key("cost", "commodities", ['Commodity', 'Name'])
input_schema.add_foreign_key("inflow", "commodities", ['Commodity', 'Name'])
input_schema.add_foreign_key("inflow", "nodes", ['Node', 'Name'])

# Define the data types
input_schema.set_data_type("commodities", "Volume", min=0, max=float("inf"),
                           inclusive_min=False, inclusive_max=False)
input_schema.set_data_type("arcs", "Capacity", min=0, max=float("inf"),
                           inclusive_min=True, inclusive_max=True)
input_schema.set_data_type("cost", "Cost", min=0, max=float("inf"),
                           inclusive_min=True, inclusive_max=False)
input_schema.set_data_type("inflow", "Quantity", min=-float("inf"), max=float("inf"),
                           inclusive_min=False, inclusive_max=False)

# The default-default of zero makes sense everywhere except for Capacity
input_schema.set_default_value("arcs", "Capacity", float("inf"))
# ---------------------------------------------------------------------------------

# ------------------------ define the output schema -------------------------------
solution_schema = TicDatFactory(
        flow=[["Commodity", "Source", "Destination"], ["Quantity"]],
        parameters=[["Parameter"], ["Value"]])
# ---------------------------------------------------------------------------------

# ------------------------ solving section-----------------------------------------
def solve(dat):
    """
    core solving routine
    :param dat: a good ticdat for the input_schema
    :return: a good ticdat for the solution_schema, or None
    """
    assert input_schema.good_tic_dat_object(dat)
    assert not input_schema.find_foreign_key_failures(dat)
    assert not input_schema.find_data_type_failures(dat)

    model = pulp.LpProblem(name="netflow", sense=pulp.LpMinimize)

    flow = {(h, i, j): pulp.LpVariable(name=f"flow_{h}_{i}_{j}", cat=pulp.LpContinuous, lowBound=0)
            for h, i, j in dat.cost if (i,j) in dat.arcs}

    flowslice = Slicer(flow)

    # Arc Capacity constraints
    for i,j in dat.arcs:
        model.addConstraint(pulp.LpConstraint(
                            e=pulp.lpSum(flow[_h, _i, _j] * dat.commodities[_h]["Volume"]
                                         for _h, _i, _j in flowslice.slice('*', i, j)),
                            rhs=dat.arcs[i,j]["Capacity"],
                            name=f'cap_{i}_{j}', sense=pulp.LpConstraintLE))

    # Flow conservation constraints. Constraints are generated only for relevant pairs.
    # So we generate a conservation of flow constraint if there is negative or positive inflow
    # quantity, or at least one inbound flow variable, or at least one outbound flow variable.
    for h,j in set((h,i) for (h,i), v in dat.inflow.items() if abs(v["Quantity"]) > 0)\
               .union({(h,i) for h,i,j in flow}, {(h,j) for h,i,j in flow}):
        model.addConstraint(pulp.LpConstraint(
            e=pulp.lpSum(flow[h_i_j] for h_i_j in flowslice.slice(h,'*',j)) +
              dat.inflow.get((h, j), {"Quantity": 0})["Quantity"] -
              pulp.lpSum(flow[h_j_i] for h_j_i in flowslice.slice(h, j, '*')),
            rhs=0, # pulp isn't quite as nice as gurobipy, the rhs cannot have expressions
            sense=pulp.LpConstraintEQ,
            name=f'node_{h}_{j}'))

    model.setObjective(pulp.lpSum(flow * dat.cost[h, i, j]["Cost"]
                                 for (h, i, j), flow in flow.items()))
    model.solve()

    if pulp.LpStatus[model.status] == 'Optimal':
        rtn = solution_schema.TicDat()
        for (h, i, j), var in flow.items():
            if var.varValue > 0:
                rtn.flow[h, i, j] = var.varValue
        rtn.parameters["Total Cost"] = sum(dat.cost[h, i, j]["Cost"] * r["Quantity"]
                                           for (h, i, j), r in rtn.flow.items())
        return rtn
# ---------------------------------------------------------------------------------

# ------------------------ provide stand-alone functionality ----------------------
# when run from the command line, will read/write json/xls/csv/db/sql/mdb files
if __name__ == "__main__":
    standard_main(input_schema, solution_schema, solve)
# ---------------------------------------------------------------------------------
