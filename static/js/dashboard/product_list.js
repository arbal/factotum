$(document).ready(function () {
  var table = $('#products').DataTable({
      "serverSide": false,
      "paging": true,
      "searching": true,
      "ordering": true,
      dom: "<'row'<'col-md-4 form-inline'l><'col-md-4 form-inline'f>>" +
          "<'row'<'col-sm-12'tr>>" +
          "<'row'<'col-sm-5'i><'col-sm-7'p>>", // order the control divs
      "columns": [
          {"width": "50%"},
          {"width": "20%"},
          {"width": "30%"}
      ]
  });
});