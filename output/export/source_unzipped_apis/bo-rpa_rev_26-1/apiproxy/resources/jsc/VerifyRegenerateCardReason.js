var reasonContext = context.getVariable("RegenerateCardPayload.reason");

var getReasonsParsed = () => {
  var reasons = context.getVariable("regenerate.reasons.values");
  return reasons.split(",");  
}

var isValidReason = (reasons, reason) => reasons.indexOf(reason) != -1;

context.setVariable("isValidReason", isValidReason(getReasonsParsed(), reasonContext));
