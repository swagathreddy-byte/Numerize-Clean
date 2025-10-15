items_map = {
    "name": "Name",
    "item_name": "FullyQualifiedName",
    "is_taxable": "Taxable",
    "rate": "UnitPrice",
    "item_id": "Id",
    "item_type": "Type",
    "status": "Active",  # if keys and values are changing
    "unit": "uom"
}

bill_mapping = {
    "bills": "Bill",
    "bill_id": "Id",
    "due_date": "DueDate",
    "balance": "Balance",
    "bill_number": "DocNumber",
    "total": "TotalAmt",
    "date": "TxnDate"
}

invoice_mapping = {
    "invoice_id": "Id",
    "date": "TxnDate",
    "balance": "Balance",
    "invoice_number": "DocNumber",
    "total": "TotalAmt",
    "is_emailed": "EmailStatus",
    "discount_total": "DiscountAmt"
}

vendor_mapping = {
    "contact_id": "Id",
    "gst_no": "GSTIN",
    "vendor_name": "DisplayName",
    'gst_treatment': "GSTRegistrationType",
    "company_name": "PrintOnCheckName",
    "mobile": "BusinessNumber",
    "status": "Active"

}

bill_payment_mapping = {
    "payment_id": "Id",
    "amount": "TotalAmt",
    "date": "TxnDate",
    "payment_mode": "PayType",
    "reference_number": "DocNumber"
}

journal_mapping = {
    "journal_id": "Id",
    "total": "TotalAmt",
    "journal_date": "TxnDate",
    "notes": "PrivateNote",
}

expense_mapping = {
    "expense_id": "Id",
    "date": "TxnDate",
    "total": "TotalAmt"
}

tax_rate_mapping = {
    'tax_id': "Id",
    "tax_specific_type": "SpecialTaxType",
    "is_editable": "Active",
    "tax_specification": "Description",
    "tax_name": "Name",
    "tax_percentage": "RateValue"
}

tax_code_mapping = {
    "tax_group_id": "Id",
    "tax_group_name": "Name",
    "tax_group_percentage": "Taxable",
    "tax_type": " TaxGroup",
}

account_mapping = {
    'account_id': 'Id',
    'account_name': 'Name',
    'is_active': 'Active',
    'account_type': 'AccountType',
}
