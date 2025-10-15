REPORT_TYPE=(
    ('P_L','Profit Statement'),
    ('CL_ST','Closing Stock'),
    ('GST','GST Summary'),
    ('CON_ANA','Consumption Analysis'),
    ('S_C_R','Sales Channel Reconciliation'),
    ('SW_IN','Swiggy Invoice Level Reconciliation'),  #<= Okay?
    ('SW_DUMP','Swiggy Dump Level Reconciliation'),
    ('TDS','TDS Summary'),
    ('PUR_EFF','Purchase Efficiency')
)

STATUS_TYPE=(
    ('Initiated','Initiated'), #Created by the task manager
    ('Review','Review'), #Created by the accountant
    ('TL','TL'), #After Accountant adds comments
    ('QC','QC'), #After TL
    ('CRM','CRM'), #After QC
    ('Published','Published'), #After CRM
)

INSIGHT_CATEGORY=(
    ('Sales', 'Sales'),
    ('Purchases', 'Purchases'),
    ('Food Cost', 'Food Cost'),
    ('Expenses', 'Expenses'),
    ('Bank Transactions', 'Bank Transactions'),
    ('Others', 'Others'),
)

INSIGHT_TYPE=(
    ('Missing Information', 'Missing Information'),
    ('Trend Observations', 'Trend Observations'),
    ('Requiring Special Attention', 'Requiring Special Attention'),
    ('Inconsistencies in line items', 'Inconsistencies in line items'),
    ('Exceptions to accrual basis', 'Exceptions to accrual basis'),
    ('Others', 'Others'),  # After CRM
)