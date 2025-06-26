var accounts = []
var accountValid = false

if(context.getVariable("accountDataResponse.status.code") === 200) {
    var accounts = JSON.parse(context.getVariable("accountDataResponse").content);
} else {
    var accounts = response.content.asJSON;
}
for(var i in accounts) {
    var account = accounts[i]
    if(account.identifier !== null && account.identifier !== undefined && account.identifier.checking_account_type == "LOCAL") {
        accountValid = true;
        context.setVariable("account.id", account.identifier.account_id);
    }
}

context.setVariable("account.valid", accountValid);