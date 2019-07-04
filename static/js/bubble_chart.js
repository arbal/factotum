var bubbleColors = new Map([
    ['Arts and crafts/Office supplies', '#0079B0'],
    ['Cleaning products and household care', '#FF7B2E'],
    ['Electronics/small appliances', '#009C3A'],
    ['Home maintenance', '#E42A32'],
    ['Landscape/Yard', '#946BB9'],
    ['Personal care', '#92564E'],
    ['Pesticides', '#EC7ABF'],
    ['Pet care', '#7E7E7E'],
    ['Sports equipment', '#BFB83C'],
    ['Vehicle', '#00BDCC']
])

function bubbleChart(width, height, showLegend=true) {
    var columnForColors = "General category",
        columnForRadius = "Cumulative product count",
        bubbleSectionWidth = showLegend ? width - 270 : width;

    function chart(selection) {
        var data = selection.datum();
        var div = selection,
            svg = div.selectAll('svg');
        svg.attr('width', width)
            .attr('height', height);


        var ldat = [
                        {"title":"Level 1","x": (1/6)*bubbleSectionWidth - 30},
                        {"title":"Level 2","x": 0.5*bubbleSectionWidth - 30},
                        {"title":"Level 3","x": (5/6)*bubbleSectionWidth - 30}
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
            .style("position", "fixed")
            .style("visibility", "hidden")
            .style("color", "white")
            .style("padding", "8px")
            .style("background-color", "#626D71")
            .style("border-radius", "6px")
            .style("text-align", "center")
            .style("font-family", "sans-serif")
            .style("width", "400px")
            .text("");

        var scaleRadius = d3v4.scaleLinear().domain([d3v4.min(data, function(d) {
            return +d[columnForRadius];
        }), d3v4.max(data, function(d) {
            return +d[columnForRadius];
        })]).range([2,20]);

        var forceXSeparate = d3v4.forceX(function (d){
            if(d['PUC level']  === '1'){
                return (1/6)*bubbleSectionWidth
            } else if (d['PUC level'] === '2'){
                return 0.5*bubbleSectionWidth
            } else {
                return (5/6)*bubbleSectionWidth
            }
        }).strength(0.1)

        function forceIsolate(force, filter) {
            var initialize = force.initialize;
            force.initialize = function() { initialize.call(force, data.filter(filter)); };
            return force;
        }

        var forceCollide = d3v4.forceCollide(function(d){
            return scaleRadius(d[columnForRadius]) + 5;
        })

        var simulation = d3v4.forceSimulation(data)
            .force("charge", d3v4.forceManyBody().strength(-8))
            .force("x", d3v4.forceX(bubbleSectionWidth/2).strength(0.05))
            .force("y", d3v4.forceY(height/2).strength(0.05))
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
                .force("charge", null)
                .force("chargeOne", forceIsolate(d3v4.forceManyBody(), function(d) { return d['PUC level']  === '1'; }).strength(-8))
                .force("chargeTwo", forceIsolate(d3v4.forceManyBody(), function(d) { return d['PUC level']  === '2'; }).strength(-8))
                .force("chargeThree", forceIsolate(d3v4.forceManyBody(), function(d) { return d['PUC level']  === '3'; }).strength(-8))
                .force("x", forceXSeparate)
                .force("y", d3v4.forceY(height/2).strength(0.1))
                .alphaTarget(0.5)
                .restart()
            labels
                .style("visibility", "visible")
        })

        d3v4.select("#combine").on('click', function(){
            simulation
                .force("charge", null)
                .force("charge", d3v4.forceManyBody().strength(-8))
                .force("x", d3v4.forceX(bubbleSectionWidth/2).strength(0.1))
                .force("y", d3v4.forceY(height/2).strength(0.1))
                .alphaTarget(0.5)
                .restart()
            labels
                .style("visibility", "hidden")
        })

        if (showLegend) {
            var unique = new Set(data.map(a => a['General category']))
            var slot = 90
            var legend = svg.append('g')

            legend.append('text')
                .attr("x", bubbleSectionWidth + 20)
                .attr("y", slot)
                .style('fill','black')
                .style('font-size','16px')
                .style('text-decoration','underline')
                .style("font-weight", "bold")
                .text("General Categories")

            unique.forEach(title => {
                slot += 30;
                legend.append('text')
                    .attr("x", bubbleSectionWidth + 20)
                    .attr("y", slot)
                    .style('font-size','14px')
                    .style('fill','black')
                    .style("font-weight", "bold")
                    .text(title)
                legend.append('rect')
                    .attr('width', 12)
                    .attr('height', 12)
                    .attr('fill', bubbleColors.get(title))
                    .attr('x', bubbleSectionWidth + 5)
                    .attr('y', slot -11)
                    .attr('rx',2)
                    .attr('ry',2)
            })
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
                return bubbleColors.get(d[columnForColors])
            })
            .attr('class','bubble')
            .attr('stroke','#004d4d')
            .attr('stroke-width',0)
            .on("mouseover", function(d) {
                d3v4.select(this)
                  .transition()
                  .duration(347)
                  .attr('stroke-width',1)
                var matrix = this.getBoundingClientRect()
                tooltip.html("PUC level: " + d['PUC level'] + "<br><b>" + d['General category'] + "-</b><br><b>-" + d['Product family'] + "-</b><br><b>-" + d['Product type'] + "</b><br>" + "Product Count: " + d[columnForRadius])
                    .style("left", (matrix.x + matrix.width + 15) + "px")
                    .style("top", (matrix.y + matrix.height - 30) + "px");
                return tooltip.style("visibility", "visible");
            })
            .on("mouseout", function() {
                d3v4.select(this)
                  .transition()
                  .duration(347)
                  .attr('stroke-width',0)
                return tooltip.style("visibility", "hidden");
            })
            .on("click", function(d) {
                location.href = d['url'];
            });
    }

    return chart;
}
