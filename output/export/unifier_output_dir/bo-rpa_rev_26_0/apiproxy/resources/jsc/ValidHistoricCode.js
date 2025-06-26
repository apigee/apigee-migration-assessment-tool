var requestPath = context.getVariable("request.path")
var historic = context.getVariable("payload.historic")

function parseStringToIntArray(codes) {
    return codes.split(",").map(x => parseInt(x))
}

function contains(codes, code) {
    return codes.indexOf(parseInt(code)) != -1
}

function validHistoricCode(code) {
    switch (requestPath) {
        case '/bo-rpa/checking-account/debit/fraud':
            context.setVariable("errorType", "DEBIT_FRAUD_INVALID_HISTORIC")
            return contains(parseStringToIntArray(context.getVariable("fraud.historic.codes")), code);
            
        case '/bo-rpa/checking-account/debit/paygo':
            context.setVariable("errorType", "DEBIT_PAYGO_INVALID_HISTORIC")
            return contains(parseStringToIntArray(context.getVariable("paygo.debit.historic.codes")), code);
            
        case '/bo-rpa/checking-account/debit/card/fee':
            context.setVariable("errorType", "DEBIT_FEE_CARD_INVALID_HISTORIC")
            return contains(parseStringToIntArray(context.getVariable("fee.card.debit.historic.codes")), code);

        case '/bo-rpa/checking-account/credit/paygo':
            context.setVariable("errorType", "CREDIT_PAYGO_INVALID_HISTORIC")
            return contains(parseStringToIntArray(context.getVariable("paygo.credit.historic.codes")), code);
            
        case '/bo-rpa/checking-account/credit/bill':
            context.setVariable("errorType", "CREDIT_BILL_INVALID_HISTORIC")
            return contains(parseStringToIntArray(context.getVariable("bill.credit.historic.codes")), code);
            
        case '/bo-rpa/checking-account/credit/cashback-atomos':
            context.setVariable("errorType", "CREDIT_CASHBACK_ATOMOS_INVALID_HISTORIC")
            return contains(parseStringToIntArray(context.getVariable("cashback.atomos.credit.historic.codes")), code);    
            
        default:
            return false; 
    }   
}

context.setVariable("isValidCode", validHistoricCode(historic))
