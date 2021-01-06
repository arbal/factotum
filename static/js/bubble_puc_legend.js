$(document).ready(function(){
  document.querySelectorAll(".puc-nav-title").forEach(title => {
    title.addEventListener('click', event => {
        var puc_id = title.getAttribute('data-puc-id');
        var puc_kind = title.getAttribute('data-puc-kind');
        // the Nested Bubble Chart that should change is the one that's associated with the legend
        // choose fobc, arbc, or ocbc depending on "FO" or "AR"
        nbc = (puc_kind == "FO" ? fobc : (puc_kind == "AR" ? arbc : ocbc))
        nbc.zoomToNode(puc_id)
    })
  });
  document.querySelectorAll(".puc-link").forEach(puc => {
    var gen_cat = puc.getAttribute('data-gen-cat');
    puc.style.backgroundColor = getPucColor(gen_cat);
  });

});
