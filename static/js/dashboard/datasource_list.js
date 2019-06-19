$(document).ready(function () {
  var table = $('#sources').DataTable({
  "lengthMenu": [ 25, 50, 75, 100 ], // change number of records shown
  "columnDefs": [
      {
          "targets": 5, // sixth column is edit/delete links
          "orderable": false
      },
      {
          "orderDataType": "dom-select",
          "targets": 3, // third column is select input
          "type": "string",
      },
  ],
  dom:"<'row'<'col-md-4 form-inline'l><'col-md-4 form-inline'f><'col-md-4'B>>" +
      "<'row'<'col-sm-12'tr>>" +
      "<'row'<'col-sm-5'i><'col-sm-7'p>>", // order the control divs
  buttons: [{
    extend: 'csv',
    text: 'Download CSV',
    title: 'Data_Sources_Factotum',
    exportOptions : {
      columns: [ 0, 1, 2, 3, 4 ],
      format: {
        body: function( data, row, col, node ) {
          if (col == 3) {
            return table
              .cell( {row: row, column: col} )
              .nodes()
              .to$()
              .find(':selected')
              .text()
           } else {
              return table
                .cell( {row: row, column: col} )
                .nodes()
                .to$()
                .text()
                .replace(/\n/g, '')
            }
          }
        }
      },
    }]
  });
});
// this grabs the val out of the select tag (Priority) in the form for sorting
$.fn.dataTable.ext.order['dom-select'] = function (settings, col) {
return this.api().column(col, { order: 'index' }).nodes().map(function (td, i) {
    return $('select', td).val();
});
};
