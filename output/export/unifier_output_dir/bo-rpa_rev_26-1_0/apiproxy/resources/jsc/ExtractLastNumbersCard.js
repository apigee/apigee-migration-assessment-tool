var json = response.content.asJSON

function isNotEmpty(array) {
    return array !== null && array.length > 0
}

if(isNotEmpty(json.cards)) {
    var subCards = json.cards[0].cards
    if(isNotEmpty(subCards)) {
        context.setVariable("card.last_number_card", subCards[0].card_number.substring(subCards[0].card_number.length - 4));
    }
}