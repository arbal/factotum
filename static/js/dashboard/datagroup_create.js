  $(document).ready(function () {
      $(document).on('click', '.allow-focus .dropdown-menu', function (e) {
        e.stopPropagation();
      });
    });
