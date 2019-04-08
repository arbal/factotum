$(document).ready(function () {
  var table = $('#chemical_presence_table').DataTable({
  // "lengthMenu": [ 10, 25, 50, 75, 100 ], // change number of records shown
  "columnDefs": [
      {
          "targets": 3,
          "orderable": false
      }
  ],
  dom:"<'row'<'col-md-4 form-inline'l><'col-md-4 form-inline'f>>" +
      "<'row'<'col-sm-12 text-center'tr>>" +
      "<'row'<'col-sm-5'i><'col-sm-7'p>>" // order the control divs
  });
});
