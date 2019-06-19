function textFlip(anchor, displayDiv, hiddenDiv) {
  var x = document.getElementById(anchor);
  var y = document.getElementById(hiddenDiv);
  var z = document.getElementById(displayDiv);
  if (x.innerHTML === "less") {
      x.innerHTML = "more";
      y.style.display = "none";
      z.style.display = "inline";
  } 
  else {
      x.innerHTML = "less";
      y.style.display = "inline";
      z.style.display = "none";
  }
}