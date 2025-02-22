# CPUNK_Airdropper
Cellframe CF20 based airdropper for CPUNK distribution

This program will take a snapshot of the entire CF20 ledger and distribute CPUNK tokens to every wallet in CF20.

Usage explanation:

check_online_status():
    Checks if cellframe-node is running in the background, it's ONLINE and 100% synced.
    
empty_database()
    Opens our previously made database and empties it. If we run our program for the first
    time, this will create the missing database.

take_snapshot()
    Dumps entire CF20 ledger into our database. We take wallet addresses and looks how many 
    CELL / mCELL they have and database them also.

investigate_ledger()
    Prints some information about the airdrop we are about to make. We do some costs estimations
    and also examine how long the airdrop program is going to run. Feel free to play with these
    values as you wish. This function does not really do anything with real tokens.

airdrop()
    Does the actual airdrop. We take 1 wallet from our database. Check if it has empty transaction hash
    column (that means this wallet has not received any airdrop yet) and sends CPUNK tokens to it.
    The amount we are sending is declared in the line 427 
    amount = 0.05                        #amount of CPUNK we are going to airdrop
    Above that line we have declared the name of the sending wallet. We do not do any checking if there
    from_wallet = "ThisIsMyWallet_01"
    is enough balance left. That you need to do by your self.
    Program then receives a transaction hash from the transaction which we just did. It looks into the 
    mempool and sees if our transaction is still there. If it is, it will wait 30 seconds and looks again.
    It usually takes about 1-3 checkings until the transaction leaves the mempool.
    After it has left the mempool, we will write that transaction hash into our database and do another drop.

check_airdropped_transactions()
    After our airdrop has been done (which can last for days) we can double check every transaction in our
    database with this function. It takes tx_hash from database and opens corresponding transaction dump.
    If the transaction status = "ACCEPTED", good, do nothing and check next one.
    If it's "DECLINED" then remove tx_hash from the database so we can try to resend it later.

After all is done, we have database full of addresses and transaction hashes. There could be few lines which
didn't receive the airdrop (DECLINED from above function). In this case we can just run airdop() function again
as it will only do new transactions when there is empty tx_hash column.

If you want to play with this program, make sure you have 2 wallets. Put you own wallet name into line 426
(from_wallet) and uncomment these lines 448 - 450. Remember to change your 2nd wallet address here. Now the
program will not check transaction hashes from database and it will send CPUNK between your 2 wallets. You only
pay small tx fee in CELLs.
            #to_wallet = "Rj7J7MiX2bWy8sNyYZeSLFi8934jQb6jwKcYubvV3LBBiut5PmP3nqgRiXcR22X9XWA4ywocMxZETnHcMvBizb9eRYt1ztv8jsLpKUXc"
            #transaction_hash = ""
            #amount = 0.05
    
    
