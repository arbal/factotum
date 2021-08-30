$('#funcuse-add').click(function (e) {
    $('.mystical').filter(':first').removeClass("mystical");
    if ($('.mystical').filter(':first').length == 0){
        $('#funcuse-add').hide();
    }
})

$('#statvalue-add').click(function (e) {
    $('.mystical').filter(':first').removeClass("mystical");
    if ($('.mystical').filter(':first').length == 0){
        $('#statvalue-add').hide();
    }
})