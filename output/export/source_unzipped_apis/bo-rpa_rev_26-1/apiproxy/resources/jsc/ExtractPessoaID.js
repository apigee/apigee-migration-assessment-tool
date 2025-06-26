 var json = JSON.parse(context.getVariable("coreBankingResponse.content"))
 var id_pessoa = json.core_banking.idPessoa
 
 context.setVariable("id_pessoa", id_pessoa);