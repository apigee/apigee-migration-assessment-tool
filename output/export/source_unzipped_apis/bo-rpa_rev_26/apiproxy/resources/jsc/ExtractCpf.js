 var cpf = context.getVariable("payload.cpf")
 
 if(cpf.length === 11) {
     context.setVariable("cpfFormat", cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4"))
     context.setVariable("validCpf", true)
 } else {
     context.setVariable("validCpf", false)
 }