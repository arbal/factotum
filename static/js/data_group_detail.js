  $(document).ready(function () {
    var table = $('#docs').DataTable({
      "serverSide": false,
      "paging": false,
      "searching": false,
      "ordering": true,
      "dom": 't'
    });

    var dg_name = document.getElementById("dg_name").value;

    $("#xx").on('click', function (event) {
        exportTableToCSV.apply(this, [$('#extract'), dg_name + '_extract_template.csv']);
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
    $('#extract_form').on('shown.bs.collapse', function () {
          this.scrollIntoView({ behavior: 'smooth'});
    });

    // scroll the clean composition data form into view when toggled
    $('#clean_comp_data_form').on('shown.bs.collapse', function () {
          this.scrollIntoView({ behavior: 'smooth'});
    });

    });
