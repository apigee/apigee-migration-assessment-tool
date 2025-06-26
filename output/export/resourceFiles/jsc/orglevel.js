// Define your JavaScript function
function myFunction(context) {
    // Access request and response objects
    var request = context.getVariable("request");
    var response = context.getVariable("response");

    // Log the request payload
    var requestBody = request.body;
    console.log("Request Body: " + requestBody);

    // Manipulate response headers
    response.headers["Content-Type"] = "application/json";

    // Set a custom response body
    var responseBody = {
        message: "Hello from Apigee JavaScript Callout!"
    };
    response.body = JSON.stringify(responseBody);
}

// Execute your function
myFunction(context);
