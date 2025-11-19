import streamlit as st
from sympy import symbols, And, Or, Not, simplify_logic
from sympy.logic.inference import satisfiable
import graphviz
import pandas as pd
import streamlit.components.v1 as components

st.set_page_config(page_title="HOL Hardware Verification Simulator", layout="wide")
st.title("🚀 HOL Hardware Verification Simulator with Clickable HOL Proof Tree & Temporal Abstraction")

# ----------------------------
# Sidebar: Define Sub-Circuits
# ----------------------------
st.sidebar.header("Define Sub-Circuits")
num_subcircuits = st.sidebar.number_input("Number of Sub-Circuits", min_value=1, max_value=3, value=1)

subcircuits = {}
for i in range(1, num_subcircuits + 1):
    sc_name = st.sidebar.text_input(f"Sub-Circuit {i} Name", f"SC{i}")
    num_components = st.sidebar.number_input(f"Components in {sc_name}", min_value=1, max_value=3, value=1, key=i)
    components_dict = {}
    for j in range(1, num_components + 1):
        comp_name = st.sidebar.text_input(f"{sc_name} - Component {j} Name", f"C{i}{j}", key=f"{i}{j}")
        input_vars = st.sidebar.text_input(f"{comp_name} Inputs (comma separated)", "A,B", key=f"{i}{j}i").split(',')
        output_var = st.sidebar.text_input(f"{comp_name} Output Var", f"Y{i}{j}", key=f"{i}{j}o")
        expr = st.sidebar.text_input(f"{comp_name} Boolean Expression", f"{output_var} = And({','.join(input_vars)})", key=f"{i}{j}e")
        delay = st.sidebar.number_input(f"{comp_name} Delay (time units)", min_value=0, max_value=5, value=0, key=f"{i}{j}d")
        components_dict[comp_name] = {"inputs": input_vars, "output": output_var, "expr": expr, "delay": delay}
    subcircuits[sc_name] = components_dict

# ----------------------------
# Display Sub-Circuits
# ----------------------------
st.header("Defined Sub-Circuits")
for sc_name, comps in subcircuits.items():
    st.subheader(sc_name)
    for cname, comp in comps.items():
        st.markdown(f"**{cname}**: Inputs={comp['inputs']}, Output={comp['output']}, Expr=`{comp['expr']}`, Delay={comp['delay']}")

# ----------------------------
# Hierarchical Circuit Composition
# ----------------------------
st.header("Hierarchical Circuit Composition")
top_level_exprs = []
for sc_name, comps in subcircuits.items():
    for comp in comps.values():
        top_level_exprs.append(comp['expr'].split('=')[1].strip())

full_circuit_expr = " & ".join(top_level_exprs)
st.markdown(f"**Top-Level Circuit Expression:** {full_circuit_expr}")

# ----------------------------
# HOL Verification with Temporal Abstraction
# ----------------------------
st.header("HOL Verification & Temporal Simulation")
try:
    # Collect variables
    all_vars = set()
    for comps in subcircuits.values():
        for comp in comps.values():
            all_vars.update(comp['inputs'])
            all_vars.add(comp['output'])

    syms = symbols(list(all_vars))
    var_map = {str(s): s for s in syms}

    # Evaluate sub-circuits
    evaluated_exprs = []
    temporal_info = {}
    for comps in subcircuits.values():
        for comp in comps.values():
            expr_str = comp['expr'].split('=')[1].strip()
            for k, v in var_map.items():
                expr_str = expr_str.replace(k, f"var_map['{k}']")
            evaluated_exprs.append(eval(expr_str))
            temporal_info[comp['output']] = comp['delay']

    # Combine top-level circuit
    circuit_logic = And(*evaluated_exprs)
    simplified = simplify_logic(circuit_logic, form='dnf')
    st.markdown(f"**Simplified Circuit Expression (DNF):** {simplified}")

    # Satisfiability
    sat = satisfiable(circuit_logic)
    if sat:
        st.success(f"Circuit is logically satisfiable ✅ Example: {sat}")
    else:
        st.error("Circuit is NOT satisfiable ❌")

    # Temporal Simulation
    st.subheader("Temporal Simulation (Unit Delay)")
    t_steps = 3
    sim_table = {var: [0]*t_steps for var in all_vars}
    for comp_output, delay in temporal_info.items():
        for t in range(delay, t_steps):
            sim_table[comp_output][t] = 1
    st.dataframe(pd.DataFrame(sim_table, index=[f"t={i}" for i in range(t_steps)]))

    # ----------------------------
    # Interactive HOL Proof Tree
    # ----------------------------
    st.header("Interactive HOL Proof Tree (Click Node)")

    # Build tree with explanations
    node_explanations = {}

    def describe_expr(expr):
        if isinstance(expr, And):
            return f"AND combines: {expr.args}"
        elif isinstance(expr, Or):
            return f"OR combines: {expr.args}"
        elif isinstance(expr, Not):
            return f"NOT of: {expr.args[0]}"
        else:
            return f"Primitive output: {expr}"

    def build_proof_tree_clickable(expr, parent=None, counter=[0], dot=None):
        if dot is None:
            dot = graphviz.Digraph(comment='HOL Proof Tree')
        node_id = f"n{counter[0]}"
        counter[0] += 1
        explanation = describe_expr(expr)
        node_explanations[node_id] = explanation
        # Add clickable HTML link using URL node
        dot.node(node_id, label=str(expr), URL=f"#{node_id}", tooltip=explanation)
        if parent:
            dot.edge(parent, node_id)
        if isinstance(expr, And) or isinstance(expr, Or):
            for arg in expr.args:
                build_proof_tree_clickable(arg, node_id, counter, dot)
        elif isinstance(expr, Not):
            build_proof_tree_clickable(expr.args[0], node_id, counter, dot)
        return dot

    proof_dot = build_proof_tree_clickable(circuit_logic)
    # Render as HTML
    proof_html = proof_dot.pipe(format='svg').decode('utf-8')

    # Embed HTML for clickable nodes
    components.html(proof_html, height=600)

    # Node selection panel
    st.subheader("Click Node Simulation")
    st.markdown("Hover over nodes to see tooltip explanations in the SVG above.")

except Exception as e:
    st.error(f"Error: {e}")

# ----------------------------
# Circuit Diagram
# ----------------------------
st.header("Circuit Visualization")
dot = graphviz.Digraph(comment='Hierarchical Circuit Diagram')
for comps in subcircuits.values():
    for comp in comps.values():
        dot.node(comp['output'], f"{comp['output']} ({comp['delay']}t)")
        for inp in comp['inputs']:
            dot.edge(inp, comp['output'])
st.graphviz_chart(dot)
