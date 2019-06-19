 var dgmenu = document.getElementById( 'id_data_group' );
 dgmenu.onchange = function() {
     console.log(this.options[ this.selectedIndex ].value )
      window.location.assign( "/dl_raw_chems_dg/" + this.options[ this.selectedIndex ].value );
 };
