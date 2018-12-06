function bubbleChart() {
    var width = 1080,
        height = 500,
        maxRadius = 6,
        columnForColors = "gen_cat",
        columnForRadius = "num_prods";

    function chart(selection) {
        var data = selection.datum();
        var legendColors = [];
        var div = selection,
            svg = div.selectAll('svg');
        svg.attr('width', width)
            .attr('height', height);

        var ldat = [
                      {"title":"Level 1","x":80},
                      {"title":"Level 2","x":347},
                      {"title":"Level 3","x":620}
                    ]

        var labels = svg.selectAll('text')
                .data(ldat)
                .enter()
            .append('text')
                .attr('y',30)
                .attr('x', function(d){ return d.x })
                .style('fill','grey')
                .style('font-size','20px')
                .style("visibility", "hidden")
                .text(function(d){ return d.title })
        
        var tooltip = selection
            .append("div")
            .style("position", "absolute")
            .style("visibility", "hidden")
            .style("color", "white")
            .style("padding", "8px")
            .style("background-color", "#626D71")
            .style("border-radius", "6px")
            .style("text-align", "center")
            .style("font-family", "sans-serif")
            .style("width", "400px")
            .text("");

        var scaleRadius = d3v4.scaleSqrt().domain([d3v4.min(data, function(d) {
            return +d[columnForRadius];
        }), d3v4.max(data, function(d) {
            return +d[columnForRadius];
        })]).range([2,20]);
        var colorCircles = d3v4.scaleOrdinal(d3v4.schemeCategory10)




        var forceXSeparate = d3v4.forceX(function (d){
            if(d.PUC_type === '1'){
                return 180
            } else if (d.PUC_type === '2'){
                return 420
            } else {
                return 620
            }
        }).strength(0.08)

        var forceXCombine = d3v4.forceX(width / 2).strength(0.05)

        var forceCollide = d3v4.forceCollide(function(d){
            return scaleRadius(d[columnForRadius]) + 5;
        })

        var simulation = d3v4.forceSimulation(data)
            // .force("charge", d3v4.forceManyBody().strength([-50]))
            .force('charge', d3v4.forceManyBody().strength(-8))
            .force("x", forceXCombine)
            .force("y", d3v4.forceY(height / 2).strength(0.05))
            .force("collide", forceCollide)
            .on("tick", ticked);

        function ticked(e) {
            node.attr("cx", function(d) {
                    return d.x;
                })
                .attr("cy", function(d) {
                    return d.y;
                });
        }
        d3v4.select("#split").on('click', function(){
            simulation
                .force("x", forceXSeparate)
                .alphaTarget(0.5)
                .restart()
            labels
                .style("visibility", "visible")
        })

        d3v4.select("#combine").on('click', function(){
            simulation
                .force("x", forceXCombine)
                .alphaTarget(0.5)
                .restart()
            labels
                .style("visibility", "hidden")
        })



        let result = data.map(a => a.gen_cat);
        function onlyUnique(value, index, self) {
            return self.indexOf(value) === index;
        }
        var unique = result.filter( onlyUnique );
        var colors = unique.map(a => colorCircles(a));

        for (i=0; i<unique.length; i++) {
            legendColors.push({title:unique[i], color:colors[i]})
        }

        var slot = 90
        var legend = svg.append('g')

        legend.append('text')
          .attr("x", 807)
          .attr("y", slot)
          .style('fill','black')
          .style('font-size','16px')
          .style('text-decoration','underline')
          .style("font-weight", "bold")
          .text("General Categories")

        for (var i = 0;i<legendColors.length;i++){
          console.log(i);
          slot += 30;
          legend.append('text')
            .attr("x", 807)
            .attr("y", slot)
            .style('font-size','14px')
            .style('fill','black')
            .style("font-weight", "bold")
            .text(legendColors[i].title)
          legend.append('rect')
            .attr('width', 12)
            .attr('height', 12)
            .attr('fill', legendColors[i].color)
            .attr('x',793)
            .attr('y', slot -11)
            .attr('rx',2)
            .attr('ry',2)
        }

        var node = svg.selectAll("circle")
            .data(data)
            .enter()
            .append("circle")
            .attr('r', function(d) {
                // alert(d)
                return scaleRadius(d[columnForRadius]) + 4
            })
            .style("fill", function(d) {
                return colorCircles(d[columnForColors])
            })
            .attr('class','bubble')
            .attr('stroke','#004d4d')
            .attr('stroke-width',0)
            .on("mouseover", function(d) {
                d3v4.select(this)
                  .transition()
                  .duration(347)
                  .attr('stroke-width',1)
                var matrix = this.getScreenCTM()
                    .translate(+ this.getAttribute("cx"), + this.getAttribute("cy"));
                    console.log(matrix)
                tooltip.html("PUC Level: " + d.PUC_type + "<br><b>" + d.gen_cat + "-</b><br><b>-" + d.prod_fam + "-</b><br><b>-" + d.prod_type + "</b><br>" + "Product Count: " + d[columnForRadius])
                    .style("left", (window.pageXOffset + matrix.e + 15) + "px")
                    .style("top", (window.pageYOffset + matrix.f - 30) + "px");
                return tooltip.style("visibility", "visible");
            })
            .on("mouseout", function() {
                d3v4.select(this)
                  .transition()
                  .duration(347)
                  .attr('stroke-width',0)
                return tooltip.style("visibility", "hidden");
            });
    }

    return chart;
}
