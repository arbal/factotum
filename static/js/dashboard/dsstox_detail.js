$(document).ready(function(){
  $('[data-toggle="tooltip"]').tooltip();
  document.querySelectorAll(".puc-link").forEach(puc => {
    var gen_cat = puc.getAttribute('data-gen-cat');
    puc.style.backgroundColor = pucColors.get(gen_cat)
  })
});

$('.handle').on('click', function (e) {
  $(this).find('svg').toggleClass('d-none');
});
