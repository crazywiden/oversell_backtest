use ultrathink mode to do the following: 

1. Parse the input: "$ARGUMENTS"
2. Extract the first number found—this is the **Agent Count**.
3. The remaining text is the **Task Description**.

Start **[Agent Count]** frontend-planner agents. Each agent should independently design for the following task:
"[Task Description]"

After generating **[Agent Count]** independent plans, first write down the plan. Then each agent should also review the plans that generated from the other agents and left comment at the end of the plans. The output will be 2 docs:
1. The **[Agent Count]** independent plans with cross review results and final plan summary
2. The detailed implementation plan doc