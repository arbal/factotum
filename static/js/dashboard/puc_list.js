var rows = JSON.parse(document.getElementById('tabledata').textContent);

var columnDefs = [
  {headerName: "Kind", field: "kind__name"},
  {headerName: "Gen Cat", field: "gen_cat"},
  {headerName: "Prod Fam", field: "prod_fam"},
  {headerName: "Prod Type", field: "prod_type"},
  {headerName: "Product Count", field: "product_count"},
  {headerName: "View Detail", cellRenderer: "detailRenderer"},
];

var rowData = rows;

// let the grid know which columns and what data to use
var gridOptions = {
  defaultColDef: {
    sortable: true,
    resizable: true,
    filter: true,
  },
  columnDefs: columnDefs,
  rowData: rowData,
  components: {
    'detailRenderer': DetailRenderer,
  },
  domLayout: 'autoHeight',
  pagination: true,
  paginationPageSize: 50,
  onGridReady: function (params) {
    // Enable column resize on load
    params.api.sizeColumnsToFit();

    // Enable column resize on page size changepaginationPageSize
    window.addEventListener('resize', function() {
      setTimeout(function() {
        params.api.sizeColumnsToFit();
      })
    })
  },
};

// cell renderer class
function DetailRenderer() {}

// init method gets the details of the cell to be rendered
DetailRenderer.prototype.init = function(params) {
    this.eGui = document.createElement('div');
    this.eGui.classList.add('d-flex', 'justify-content-between');
    var text = (
        '<a class="btn btn-primary btn-sm" role="button" title="View PUC Detail" href="/puc/' + params.data.id + '">' +
            '<i class="fa fa-sitemap"></i>' +
        '</a>'
    );
    this.eGui.innerHTML = text;
};

DetailRenderer.prototype.getGui = function() {
    return this.eGui;
};

//Clear all filters
function clearFilters() {
  gridOptions.api.setFilterModel(null);
}

//Filter search box
function onFilterTextBoxChanged() {
    gridOptions.api.setQuickFilter(document.getElementById('filter-text-box').value);
}

//Change the amount of rows to paginate table
function onPageSizeChanged(newPageSize) {
  var value = document.getElementById('page-size').value;
  if(value == "All"){
      // this.clearFilters()
      value = gridOptions.api.paginationGetRowCount()
  }
  gridOptions.api.paginationSetPageSize(Number(value));
}

// setup the grid after the page has finished loading
document.addEventListener('DOMContentLoaded', function() {
    var gridDiv = document.querySelector('#pucGrid');
    new agGrid.Grid(gridDiv, gridOptions);
});

