CYCLE_TYPE=(
    ('MONTHLY','Monthly'),
    ('WEEKLY','Weekly'),
    ('DAILY','Daily'),
    ('QUARTERLY','Quarterly'),
    ('YEARLY','Yearly'),
)

INPUT_TYPE=(
    ('BY_BRAND','By brand'),
    ('BY_OUTLET','By outlet'),
    ('BY_ENTITY','By entity'),
    ('BY_CUSTOMER','By customer'),
)

SUBSCRIPTION_REPORT_TYPE=(
    ('P_L','Profit Statement'),
    ('GST','GST Summary'),
    ('PUR_EFF','Purchase Efficiency'),
    ('CON_ANA','Consumption Analysis'),
    ('S_C_R','Sales Channel Reconciliation'),
    ('SW_DUMP','Swiggy Dump Level Reconciliation'),
)

SUBSCRIPTIONS=[
    {
        "name":"P_L",
        "frequency":"monthly",
        "granularity":"outlet"
    },
    {
        "name":"GST",
        "frequency":"monthly",
        "granularity":"outlet"
    },
    {
        "name":"PUR_EFF",
        "frequency":"monthly",
        "granularity":"customer"
    },
    {
        "name":"CON_ANA",
        "frequency":"monthly",
        "granularity":"outlet"
    },
    {
        "name":"S_C_R",
        "frequency":"monthly",
        "granularity":"customer"
    },
    {
        "name":"SW_DUMP",
        "frequency":"monthly",
        "granularity":"customer"
    },
]

