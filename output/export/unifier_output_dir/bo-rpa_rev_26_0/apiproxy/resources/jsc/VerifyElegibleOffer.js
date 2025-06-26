var products = []
var hasPaymentAccount = false
var hasPaymentPostpaid = false
var hasUpgradedAccount = false

if(context.getVariable("productDataResponse.status.code") === 200) {
    var products = JSON.parse(context.getVariable("productDataResponse").content);
} else {
    var products = response.content.asJSON;
}

for(i in products) {
    var product = products[i]
    hasPaymentAccount = hasPaymentAccount || "PAYMENT_ACCOUNT" == product
    hasPaymentPostpaid = hasPaymentPostpaid || "PAYMENT_POSTPAID" == product
    hasUpgradedAccount = hasUpgradedAccount || "CHECKING_ACCOUNT" == product
}

context.setVariable("products.payment_account", hasPaymentAccount);
context.setVariable("products.payment_postpaid", hasPaymentPostpaid);
context.setVariable("products.upgraded_account", hasUpgradedAccount);