// Base64 encode search query
$('#factotum-search-form').submit(function (event) {
    var url = new URL(window.location.origin + "/search/product/");
    url.search = "?q=" + btoa($("#q").val());
    window.location = url;
});