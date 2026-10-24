"""Notes and activities for the timeline (all phases). Idempotent; reads the PAC_* environment variables.

Activities only where users plan or log work with others (Project); notes with @mentions on the main records.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from meta import enable_timeline, publish

ACTIVITIES = ['op365_project']
NOTES = ['op365_wbsnode', 'op365_item', 'op365_resource', 'op365_purchaserequest', 'op365_rfq', 'op365_purchaseorder',
         'op365_goodsreceipt', 'op365_supplierinvoice']

for table in ACTIVITIES:
    enable_timeline(table, activities=True)
for table in NOTES:
    try:
        enable_timeline(table)
    except KeyError:
        print('skip timeline', table, '(table not created yet)')
publish()
