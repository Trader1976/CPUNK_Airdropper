import sqlite3
import operator
import re
import time
import subprocess
import json
import socket
#                      /|      __
#*             +      / |   ,-~ /             +
#     .              Y :|  //  /                .         *
#         .          | jj /( .^     *
#               *    >-"~"-v"              .        *        .
#*                  /       Y
#   .     .        jo  o    |     .            +
#                 ( ~T~     j                     +     .
#      +           >._-' _./         +
#               /| ;-"~ _  l
#  .           / l/ ,-"~    \     +        C P U N K   A I R D R O P P E R
#              \//\/      .- \                        V1.2
#       +       Y        /    Y          This program requires Cellframe node
#               l       I     !          which is online and 100% synced to the
#               ]\      _\    /"\        chain. It will take a snapshot and distribute
#              (" ~----( ~   Y.  )       some CPUNK tokens to every wallet in CF20 ledger.
#          ~~~~~~~~~~~~~~~~~~~~~~~~~~    USE AT YOUR OWN RISK. I'm a punk... a C punk.
# Other requirements : sqlite3 and balls of steel to actually run the airdrop from your wallet.
# Added feature : mempool checking. After every transaction, we will look into mempool and wait
# until our transaction has left. Only after that we make another transaction.
def investigate_ledger():
    """Shows some data from CF20 CELL ledger
    """
    db_path = r"airdrop.db"
    con = sqlite3.connect(db_path)
    with con:
        cur = con.cursor()
        query = """SELECT id FROM snapshot ORDER BY id DESC LIMIT 1"""
        cur.execute(query)
        wallets, = cur.fetchone()
        print("There are currently", wallets, "wallets in CF20")

        query = """SELECT SUM(CELL_balance) FROM (SELECT CELL_balance FROM {table})""".format(table="snapshot")
        cur.execute(query)
        total_cell, = cur.fetchone()
        print("All CELL holdings (CELL + mCELL) added together", total_cell)

        query = """SELECT combined_balance FROM snapshot ORDER BY combined_balance DESC LIMIT 1"""
        cur.execute(query)
        whale_balance, = cur.fetchone()
        print("Biggest holder has", whale_balance," CELL in his wallet")

        average_balance = total_cell / wallets
        print("On average, investors hold",average_balance, "CELLs\n")


        #######################################################
        #  We can play with these numbers as much as we wish  #
        #######################################################
        airdrop_amount = 10000000
        tx_fee = 0.01
        pause_between_transactions = 90 #seconds (We wait 30 seconds after every tx and then check mempool
                                        #         ...usually ita takes 2-3 times to complete)


        airdrop_costs = tx_fee * wallets
        even_airdrop = airdrop_amount / wallets

        print("If we decide to airdrop", airdrop_amount,"CPUNKS in total (ten million)")
        print("We should do",wallets,"transactions which would cost us",airdrop_costs,"CELL in fees")
        print("...if the tx_fee is",tx_fee)
        print("If we distribute CPUNK evenly for every wallet, then everone would receive",even_airdrop,"CPUNK\n")

        proportional_airdop = airdrop_amount / total_cell

        print("For proportional airdrop, we should drop",proportional_airdop, "for every CELL in wallets")
        print("Then our Mr.Whale would receive", whale_balance*proportional_airdop,"CPUNK")
        print("And our Mr. Average would get", average_balance*proportional_airdop,"CPUNK\n")

        print("To make the actual airdrop happen, we need to make some transactions.")
        print("In order not to flood / clog the mempool, we should have a small pause between")
        print("every transaction. If we pause for",pause_between_transactions, "seconds")
        required_time = (pause_between_transactions * wallets) / 3600
        print("then the whole airdrop would take", required_time, "hours of full action.")


def check_online_status():  # stops the program if cellframe-node-cli is OFFLINE
    """Checks if master node is online

    Returns nothing if online and exits with exit code 1
    if node is offline or not responding.
    """
    states = ["NET_STATE_ONLINE", "NET_STATE_SYNC_CHAINS", "NET_STATE_SYNC_GDB"]
    print("checking")
    data = json_output("net", "net;-net;Backbone;get;status")
    if (data["result"][0]["status"]["states"]["current"]) in states:
        print("Node ONLINE")

        if data["result"]:
            status = data["result"][0]["status"]

            if status["processed"]["main"]["percent"] == "100.000 %":
                print("Main chain is 100% synced!")

        return

    else:
        print("Node is offline...terminating")
        exit(1)

def is_transaction_accepted(first_transaction):
    """Json dumps transaction and checks whether it was
       accepted or declined. If latter case, it increases
       declined transactions into DB by 1.

    Parameters: transaction hash (str)
    Returns : 1 = ACCEPTED
              0 = DECLINED
    """
    payload_tx = "tx_history;-tx;" + first_transaction + ";-net;Backbone;-chain;main"
    test = json_output("tx_history", payload_tx)

    if test["result"]:
        status = test["result"][0]["status"]
    #    print("status",status)
        if status == "ACCEPTED":
            return 1
        else:
            return 0


def check_airdropped_transactions():
    """After doing the airdrop, we'll check every signle transaction
       to see if they were ACCEPTED or DECLINED.
       If they were declined, then remove the hash from that transaction
       so we can do it again later.
    """
    db_path = r"airdrop.db"
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    with con:
        query = "SELECT id FROM snapshot ORDER BY id DESC LIMIT 1"
        cur.execute(query)
        lines, = cur.fetchone()

        for x in range(1, lines+1):
            query = "SELECT tx_hash FROM snapshot WHERE id=?"
            cur.execute(query,[x])
            hash, = cur.fetchone()
            print(hash)

            if hash == "": #if there was no tx_hash
                print("No hash")
                continue

            else:
                if is_transaction_accepted(hash) == 0:  #test if tx was ACCEPTED or DECLINED
                    print("transaction",hash,"DECLINED")
                    query = """UPDATE snapshot SET tx_hash="" WHERE id=?"""
                    cur.execute(query,[x])
                    con.commit()
                else:
                    print("ACCEPTED")
                    continue


def json_output(method, params):
    """Receives JSON output from given cellframe-node-cli command
    """
    socket_path = "/opt/cellframe-node/var/run/node_cli"
    data = json.dumps({"method": method, "params": [params], "id": "1"})
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(socket_path)
    client.sendall(bytes(f"POST /connect HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: {len(data)}\r\n\r\n{data}", 'utf-8'))
    response = b''

    client.settimeout(1)  # Timeout after 1 second
    try:
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            response += chunk
            if b'"id": 1 }' in response:  # Check for HTTP header end
                break
    except socket.timeout:
        print("Socket timed out, assuming end of response\n")

    start_index = response.find(b'{')
    json_payload = response[start_index:]

    result = dict(json.loads(json_payload.decode('utf-8')))
    client.close()
    return result


def empty_database():
    """Empties the snapshot database
    """
    db_path = r"airdrop.db"
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    with con:
        query = "DROP TABLE snapshot"  #destroy the old table...
        try:
            cur.execute(query)
            con.commit()
            create_snapshot_database()     #...and make new one
        except:
            print("Cannot find database. Let's make one.")
            create_snapshot_database()
        return


def create_snapshot_database():
    """Creates sqlite database for the ledger snapshot
    """
    sql_create_ledger_snapshot = """CREATE TABLE snapshot (
                                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                                  wallet TEXT UNIQUE,
                                  CELL_balance REAL,
                                  mCELL_balance REAL,
                                  combined_balance REAL,
                                  tx_hash TEXT,
                                  airdropped REAL
                                  );"""
    db_path = r"airdrop.db"
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(sql_create_ledger_snapshot)
    con.close()
    return


def fire_and_split_command(command, txhash, split=True):  #run our shell command (c) @hyttmi
    """Run shell subprocess command
    """
    command = command+txhash
    command = command.split()

    try:
        command_run = subprocess.run(command, timeout=5, check=True, stdout=subprocess.PIPE)
        if split:
            command_run = str(command_run.stdout, encoding="utf-8").splitlines()
        else:
            command_run = str(command_run.stdout, encoding="utf-8")

    except subprocess.TimeoutExpired:
        print("The command took too long and was terminated.")
        return None
    return command_run


def take_snapshot():  # dumps wallets from blockchain into database
    """Dumps wallets and database wallet addresses, CELL/mCELL holdings
       and then calculate CELL + (mCELL*1000) for combined balance.
    """
    db_path = 'airdrop.db'
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    with con:

        query = "cellframe-node-cli ledger list balance"
        command = fire_and_split_command(query, " -net Backbone", True)
        list_items = len(command)
        print("...dumping wallets")

        #####################################################
        # Let's go through the wallet dump line by line and #
        # get all the data we want.                         #
        #####################################################
        for x in range(2, list_items, 1):

           if "Ledger balance key:" in command[x]:

                  grab_line = command[x]
                  wallet = grab_line[32:136]  # get the wallet address
                  print(wallet)

                  # Test and see if we reallt have a genuine wallet address
                  pattern = '^[A-Za-z0-9]{104}$'
                  result = re.match(pattern, wallet)

                  if result:  # If this was a correct wallet address...get ticker and balance

                      length = len(command[x+1])
                      data = operator.getitem(command[x+1], slice(length - 5, length))  # if found, copy last 66 letters
                      ticker = data.strip() #remove whitespaces

                      balance = re.findall(r'\d+', command[x+2]) #get balance for this wallet
                      balance = int(balance[0])
                      balance = balance / 1000000000000000000

                      # Let's test if this wallet is in the database already
                      # by searching the database with wallet address
                      query = "SELECT id FROM snapshot WHERE wallet=?"
                      cur.execute(query,[wallet])
                      id = cur.fetchone()

                      if id == None:  # if this wallet was not yet in the database...

                          if ticker == "CELL": #if we have the right ticker, then database it
                              query = "INSERT INTO snapshot VALUES(null,?,?,?,?,?,?)"
                              cur.execute(query,[wallet,balance,0,0,"",0])  # put CELL wallet address and balance into DB, leave rest 0
                              con.commit()

                          if ticker == "mCELL": #if we have the right ticker, then database it
                              query = "INSERT INTO snapshot VALUES(null,?,?,?,?,?,?)"
                              cur.execute(query,[wallet,0,balance,0,"",0])  # put CELL wallet address and balance into DB, leave rest 0
                              con.commit()

                      else: #if the wallet was already in the database
                          if ticker == "CELL":  # if we have the right ticker, then database it
                              query = "UPDATE snapshot SET CELL_balance=? WHERE wallet=?"
                              cur.execute(query,[balance,wallet])
                              con.commit()

                          if ticker == "mCELL":  # if we have the right ticker, then database it
                              query = "UPDATE snapshot SET mCELL_balance=? WHERE wallet=?"
                              cur.execute(query, [balance,wallet])
                              con.commit()

                  else:
                      # Sometimes it's possible we come to here as
                      # cellframe-node-cli list ledger balance
                      # can print wrong wallet lines....like here:
                      #Ledger balance key: null RLE
                      #token_ticker: RLE
                      #balance: 1500000000000000000
                      # so we will just ignore these lines and carry on...
                      print("Something wrong in fetching wallet addresses. Please check")
                      print("output of cellframe-node-cli ledger list balance command!")
                      continue

    query = "SELECT id FROM snapshot ORDER BY id DESC LIMIT 1"
    cur.execute(query)
    lines, = cur.fetchone()
    print("We have",lines,"unique wallets")
    print("Now calculating CELL + mCELL into combined_balance...")

    for x in range(1, lines+1):
        query = "SELECT CELL_balance, mCELL_balance FROM snapshot WHERE id=?"
        cur.execute(query,[x])
        cell_balance, mcell_balance = cur.fetchone()
        total_from_mcell = mcell_balance * 1000
        grand_total = cell_balance + total_from_mcell

        query = "UPDATE snapshot SET combined_balance=? WHERE id=?"
        cur.execute(query,[grand_total,x])
        con.commit()
    print("Done")
    print("Snapshot of CF20 ledger was taken")
    return


def send(from_wallet:str, amount: float, to_wallet:str):
    """Handles the actual sending transaction.
        Parameters :
            from_wallet : wallet that sends the CPUNK and pays tx fee
            amount : amount of CPUNK to send
            to_wallet : CF20 wallet to receive the airdrop
    """
    ####################################################################
    #                                                                  #
    #  CHANGE transfer_fee as per necessary at the moment of airdrop   #
    #                                                                  #
    ####################################################################
    transfer_fee = 0.05

    # combine all the data we have into one cli command and run it
    first_part = "cellframe-node-cli tx_create -net Backbone -chain main -value " + str(amount) + "e+18 -token CPUNK "
    last_part ="-to_addr " + to_wallet + " -from_wallet " + from_wallet + " -fee " + str(transfer_fee) + "e+18"
    try:
        command = fire_and_split_command(first_part, last_part, True)
        hash = command[2][-66:]    #get returned transaction hash
        if len(hash) == 66:        #and see if it's correct length
            return hash            #and return it so we can database it

    except:
        input("Got error...terminating")
        exit(1)


def check_mempool(transaction_hash:str):
    """JSON Dumps the mempool and tries to locate our last transaction.
        Parameters :
            tx_hash : last airdrop transaction hash
            returns : 0 if transaction no longer in the mempool
                      1 if the trasaction still in the mempool
    """
    payload_tx = "mempool;list;-net;Backbone;-chain;main"
    mempool_data = json_output("mempool", payload_tx)

    total_str = mempool_data['result'][0]['chains'][0]['total']
    match = re.search(r'\d+$', total_str)

    if match: #get number of transactions in mempool
        transactions_in_mempool = int(match.group())  # Convert to integer

    for x in range(transactions_in_mempool): #search our transaction from mempool transaction hashes
        hash = mempool_data['result'][0]['chains'][0]['datums'][x]['hash']

        #if we found our transaction from the mempool
        if hash == transaction_hash:
            print("Our transaction is still in the mempool...let's wait 30 seconds")
            print("--------------------------------------------------------------------")
            print("Waiting.", end="")
            for z in range(60):
                print(".", end="")
                time.sleep(0.5)
            return 1
        else:
            pass
    return 0


def airdrop():
    """Does the actual airdrop. It looks through our database wallet by wallet
       and does the CPUNK sending transaction...according to the rules that
       are set in this function.
    """
    #########################################################################
    #                                                                       #
    #  SPECIFY HERE from wallet = wallet where airdrop is being sent from   #
    #  amount = How much CPUNK we are going to airdrop                      #
    #                                                                       #
    #########################################################################

    from_wallet = "ThisIsMyWallet_01"    #define here the name of the sending wallet
    amount = 0.05                        #amount of CPUNK we are going to airdrop

    db_path = 'airdrop.db'
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    with con:
        # get the number of lines in our database
        query = "SELECT id FROM snapshot ORDER BY id DESC LIMIT 1"
        cur.execute(query)
        lines, = cur.fetchone()
        print("Going to do an airdrop into",lines,"wallets")
        time_left = (lines * 90) / 3600
        print("It's going to take approximately",time_left,"hours")

        # ...and go through each of them
        for x in range(1, lines+1):
            query = "SELECT wallet, tx_hash FROM snapshot WHERE id=?"
            cur.execute(query,[x])
            to_wallet, transaction_hash = cur.fetchone()

            # for testing purposes, uncomment the next 3 lines and CHANGE your second wallet down below.
            #to_wallet = "Rj7J7MiX2bWy8sNyYZeSLFi8934jQb6jwKcYubvV3LBBiut5PmP3nqgRiXcR22X9XWA4ywocMxZETnHcMvBizb9eRYt1ztv8jsLpKUXc"
            #transaction_hash = ""
            #amount = 0.05

            # transaction_hash should be empty by default...but
            # If for some reason, our airdrop campaign comes to halt, we can
            # continue later as we don't send airdrop to those wallets that
            # already has it's transaction hash.
            if transaction_hash == "":
                print("Sending airdrop",x,"/",lines, "to wallet", to_wallet)
                hours = ((lines - x) * 90) / 3600
                print("Aproximately", hours,"hours to go")

                # SEND IT and receive transaction hash
                hash = send(from_wallet, amount, to_wallet)
                while check_mempool(hash) == 1: #wait until our transaction has left the mempool
                    pass
                print("Transaction", hash,"completed!")

                #update tx_hash into database
                query = "UPDATE snapshot SET tx_hash=? WHERE id=?"
                cur.execute(query,[hash,x])
                con.commit()

            else:
                print(x,"This wallet has already received the airdrop")


if __name__ == "__main__":
    check_online_status()    #Test if cellframe-node is ONLINE and 100% synced

    empty_database()        #Empty the database !!! WARNING...DO NOT USE after the airdrop!!!
    take_snapshot()         #Take a snapshot of entire CF20 ledger
    investigate_ledger()    #Throw out some calculation and other data from the ledger.
 #   airdrop()                #Does the actual airdrop. Remember to configure correctly!!!

    # After airdrop is done, run this below function. It checks every transaction
    # in our database and deletes tx_hash from the ones that were DECLINED.
    # Then run airdrop() function again. It will only resend into those wallets
    # that has tx_hash deleted.

    #check_airdropped_transactions()
