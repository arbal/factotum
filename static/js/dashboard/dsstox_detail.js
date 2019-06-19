$(document).ready(function(){
  $('[data-toggle="tooltip"]').tooltip();
  document.querySelectorAll(".puc-link").forEach(puc => {
    var gen_cat = puc.innerText.split(" - ")[0];
    puc.getElementsByClassName("puc-legend")[0].style.backgroundColor = bubbleColors.get(gen_cat)
  })
});