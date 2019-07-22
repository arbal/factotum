  $(document).ready(function () {
    var table = $('#docs').DataTable({
        "pageLength": 50,
        "serverSide": false,
        "paging": true,
        "searching": false,
        "ordering": true
    });

    // make submit button active when file selected
    $('input:file').change(
        function(){
            if ($(this).val()) {
                $('input:submit').attr('disabled',false);
            } else {
                $('input:submit').attr('disabled',true);
            }
        }
    );

    // scroll the extract form into view when toggled
    $('#extract_form').on('shown.bs.collapse', getLifted );

    // scroll the clean composition data form into view when toggled
    $('#clean_comp_data_form').on('shown.bs.collapse', getLifted );

    });

function getLifted () {
    var panel = $(this).find('.wealthy');
    $('html, body').animate({
            scrollTop: panel.offset().top - 80
    }, 347);
}
