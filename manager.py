from pprint import pprint
from steem import Steem
from steem.account import Account
from steem.commit import Commit
from steem.blockchain import Blockchain
from apscheduler.schedulers.background import BackgroundScheduler
import inspect
import os
import sys
import time

donation_account = os.environ['ico_account_donation']
wif              = os.environ['steem_wif']

process_account  = os.environ['ico_account_processed']

ico_start        = int(os.environ['ico_block_start'])
ico_end          = int(os.environ['ico_block_end'])
ico_currency     = os.environ['ico_currency']

nodes = [os.environ['steem_node']]
s = Steem(nodes, keys=[wif])

state = {
    'participants': {}
}

queue = {
    'donations': [],
    'refunds': []
}

def l(msg):
    caller = inspect.stack()[1][3]
    print("[ICOMANAGER][{}] {}".format(str(caller), str(msg)))
    sys.stdout.flush()

def refund(op):
    amount, symbol = op['amount'].split(' ')
    message = "[{}] Refund of {} {} from @{} - Only accepts {} between blocks {} and {}.".format(op['block_num'], amount, symbol, op['from'], ico_currency, ico_start, ico_end)
    s.transfer(op['from'], amount, symbol, account=donation_account, memo=message)
    l("Processed refund for {} on block {} for {} {}".format(op['from'], op['block_num'], amount, symbol))

def donation(op):
    amount, symbol = op['amount'].split(' ')
    if symbol == ico_currency:
        updateParticipants(op)
        message = "[{}] {} {} from @{}".format(op['block_num'], amount, symbol, op['from'])
        s.transfer(process_account, amount, symbol, account=donation_account, memo=message)
        l("Processed valid donation from @{} on block {} for {} {}".format(op['from'], op['block_num'], amount, symbol))
    else:
        refund(op)

def queueOp(method, op):
    l("Queueing {} operation".format(method))
    queue[method].append(op)

def processQueue():
    try:
        # Process both the donations and refunds queue
        for key in queue:
            for op in queue[key]:
                if key == 'donations':
                    donation(op)
                if key == 'refunds':
                    refund(op)
                # Remove the operation from the queue if successful
                queue[key].remove(op)

    except Exception as e:
        waiting = len(queue['donations']) + len(queue['refunds'])
        l("-------------------------------")
        l(e)
        l("!!! ERROR: transfers ({}) unabled to process - please delegate more SP to @{}".format(waiting, donation_account))
        l("-------------------------------")
        pass

def processOp(op):
    block_num = op['block_num']
    # Operation Type
    opType = op['type']
    # Only process transfer operations
    if opType == 'transfer':
        # Check where funds are being transfered
        to = op['to']
        # Check if it matches the donation account for the ICO
        if to == donation_account:
            # Check whether this operation falls within the set time period
            valid_for_ico = bool(block_num <= ico_end and block_num >= ico_start)
            # Process donation or refund
            if valid_for_ico:
                queueOp('donations', op)
                # donation(op)
            else:
                queueOp('refunds', op)
                # refund(op)

def commitParticipants():
    current = Account(donation_account)
    current_participants = current['json_metadata']['extensions']['ico']
    if state != current_participants:
        l("Committing participants to `json_metadata` on @{}".format(donation_account))
        saveState()

def updateParticipants(op):
    global state
    amount, symbol = op['amount'].split(' ')
    participant = op['from']
    if participant in state['participants']:
        state['participants'].update({
            participant: state['participants'][participant] + float(amount)
        })
    else:
        state['participants'].update({
            participant: float(amount)
        })
    l(state)
    sys.stdout.flush()

def saveState():
    current = Account(donation_account)
    profile = current['json_metadata']
    if 'extensions' not in profile:
        profile.update({
            'extensions': {
                'ico': {}
            }
        })
    if 'ico' not in profile['extensions']:
        profile['extensions'].update({
            'ico': {}
        })
    profile['extensions']['ico'] = state
    s.update_account_profile(profile, account=donation_account)


if __name__ == '__main__':
    l("-------------------------------")
    l("Configuration loaded:")
    l("    Donate funds to account: @{}".format(donation_account))
    l("    Send process funds to account: @{}".format(process_account))
    l("    Only accept donations: between blocks {} and {}".format(ico_start, ico_end))
    l("    Currency Accepted: {}".format(ico_currency))
    l("-------------------------------")

    # Ensure the account's json is initialized
    current = Account(donation_account)
    if (not isinstance(current['json_metadata'], dict)
        or 'extensions' not in current['json_metadata']
        or 'ico' not in current['json_metadata']['extensions']):
        saveState()
        l("Initialized empty participants within `json_metadata`.")
        l("-------------------------------")
    else:
        global state
        state = current['json_metadata']['extensions']['ico']
        l(state)
        l("Loaded previous participants from `json_metadata`.")
        l("-------------------------------")

    # Scheduled tasks to perform every few minutes
    scheduler = BackgroundScheduler()
    scheduler.add_job(commitParticipants, 'interval', minutes=1, id='commitParticipants')
    scheduler.add_job(processQueue, 'interval', seconds=10, id='processQueue')
    scheduler.start()


    # Watch the Blockchain
    b = Blockchain()
    for op in b.stream():
        processOp(op)
