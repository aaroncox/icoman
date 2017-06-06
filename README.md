# ICOMAN

An experimental service to manage an ICO run through STEEM. Currently the only aspect this script addresses if fund management in a way that can be audited and indexes built upon.

The methods used in this application are incredibly early in development, I wouldn't recommend using this for anything important.

This release is purely to spur discussion on how best to approach these problems.

### How it works

This application relies on two accounts (both preferably unused):

- `donation` account: The account that will receive funds from donors and process transactions.
- `processed` account: The account that all processed funds will be deposited into.

The `donation` account will require SP (to be used as gas) to process transactions, please delegate accordingly.

After configuring the service, you should prompt users to send funds in the selected currency to the donation account between the `ico_block_start` and `ico_block_end` times. Any donations outside of those blocks or sent with the wrong currency will automatically be refunded.

The service itself has a workflow as such:

- Service starts and monitors the blockchain for transactions to the `donation` account.
- Upon transaction received:
  - If within specified timeframe and correct currency symbol, continue.
  - If outside of specified timeframe, return funds to sender and ignore.
  - If incorrect currency symbol, return funds to sender and ignore.
- If transaction is valid:
  - Forward funds to the `processed` account with a memo detailing who it was from, what block, and the amount.
  - Update `donation` account's `json_metadata` to contain record of the donation. An example of this can be found on the `test-ico` account's `json_metadata`.

### Problems that need solutions still

- The `json_metadata` field on the account can only hold so much data, as can each block. This might not be a great place to maintain an index of donors and amounts. Creating `custom_json` ops that can then be indexed in the future will be a more scalable approach.
- The service currently maintains all information in memory and if the script crashes, cannot resume it's active state.
- There is no way to transfer value/tokens from one user to another using this approach. Migrating the balance information into `custom_json` ops in the future could allow for transfers of value.

### Configuration

Copy the `env-example` file to `.env` and edit the appropriate settings into place.

Example:

```
# ---- CONFIGURATION ----

# The node you'd like to use
steem_node=https://steemd.steemitdev.com

# ---- ICO SETTINGS ----

# The name of the ICO deposit account
ico_account_donation=test-ico

# The name of the ICO processed funds account
ico_account_processed=test-team

# The WIF Key for the witness account, used to sign transactions
steem_wif=5YOURPRIVATEKEYFORTHEICOACCOUNTHERE

# The block number when the ICO starts
ico_block_start=12590000

# The block number when the ICO ends
ico_block_end=12600000

# Which currency to accept
ico_currency=STEEM
```

### Running

This script is build around `docker-compose`, though could be run other ways. To start, run:

`docker-compose build && docker-compose up`
