var json = response.content.asJSON

function getId(loan) {
    var id = {
        id: loan.id
    }
  return id;
}

var id_loans = json.map(getId)

context.setVariable("id_loans", JSON.stringify(id_loans));