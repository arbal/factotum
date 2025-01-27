$(document).ready(function () {
  var table = $('#data_group_table').DataTable({
  // "lengthMenu": [ 10, 25, 50, 75, 100 ], // change number of records shown
  "columnDefs": [
      {
          "targets": [1, 4, 5],
          "orderable": false
      }
  ],
  dom:"<'row'<'col-md-4 form-inline'l><'col-md-4 form-inline'f>>" +
      "<'row'<'col-sm-12 text-center'tr>>" +
      "<'row'<'col-sm-5'i><'col-sm-7'p>>" // order the control divs
  });
});
