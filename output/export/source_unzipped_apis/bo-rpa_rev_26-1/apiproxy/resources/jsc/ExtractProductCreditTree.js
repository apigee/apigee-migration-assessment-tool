var json = response.content.asJSON;

function isTypeCard(product) {
    return product.type.includes(context.getVariable("payload.product_type"));
}

function findProductCard(category) {
    var product = category.products.find(isTypeCard);
    if (product !== null && product !== undefined) {
        context.setVariable("credit.product", JSON.stringify(product));
        context.setVariable("credit.total_limit", category.total_limit);
        return true;
    }
    return false;
}

context.setVariable("credit.product", null);
json.categories.some(findProductCard);