
var pucColors = new Map([
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

var bubbleColors = pucColors;

function bubbleChart(width, height, showLegend = true) {
    var columnForColors = "General category",
        columnForRadius = "Cumulative product count",
        bubbleSectionWidth = showLegend ? width - 270 : width;

    function chart(selection) {
        var data = selection.datum();
        var div = selection,
            svg = div.selectAll('svg');
        svg.attr('width', width)
            .attr('height', height);


        var ldat = [{
                "title": "Level 1",
                "x": (1 / 6) * bubbleSectionWidth - 30
            },
            {
                "title": "Level 2",
                "x": 0.5 * bubbleSectionWidth - 30
            },
            {
                "title": "Level 3",
                "x": (5 / 6) * bubbleSectionWidth - 30
            }
        ]

        var labels = svg.selectAll('text')
            .data(ldat)
            .enter()
            .append('text')
            .attr('y', 30)
            .attr('x', function (d) {
                return d.x
            })
            .style('fill', 'grey')
            .style('font-size', '20px')
            .style("visibility", "hidden")
            .text(function (d) {
                return d.title
            })

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

        var scaleRadius = d3v4.scaleLinear().domain([d3v4.min(data, function (d) {
            return +d[columnForRadius];
        }), d3v4.max(data, function (d) {
            return +d[columnForRadius];
        })]).range([2, 20]);

        var forceXSeparate = d3v4.forceX(function (d) {
            if (d['PUC level'] === '1') {
                return (1 / 6) * bubbleSectionWidth
            } else if (d['PUC level'] === '2') {
                return 0.5 * bubbleSectionWidth
            } else {
                return (5 / 6) * bubbleSectionWidth
            }
        }).strength(0.1)

        function forceIsolate(force, filter) {
            var initialize = force.initialize;
            force.initialize = function () {
                initialize.call(force, data.filter(filter));
            };
            return force;
        }

        var forceCollide = d3v4.forceCollide(function (d) {
            return scaleRadius(d[columnForRadius]) + 5;
        })

        var simulation = d3v4.forceSimulation(data)
            .force("charge", d3v4.forceManyBody().strength(-8))
            .force("x", d3v4.forceX(bubbleSectionWidth / 2).strength(0.05))
            .force("y", d3v4.forceY(height / 2).strength(0.05))
            .force("collide", forceCollide)
            .on("tick", ticked);

        function ticked(e) {
            node.attr("cx", function (d) {
                    return d.x;
                })
                .attr("cy", function (d) {
                    return d.y;
                });
        }
        d3v4.select("#split").on('click', function () {
            simulation
                .force("charge", null)
                .force("chargeOne", forceIsolate(d3v4.forceManyBody(), function (d) {
                    return d['PUC level'] === '1';
                }).strength(-8))
                .force("chargeTwo", forceIsolate(d3v4.forceManyBody(), function (d) {
                    return d['PUC level'] === '2';
                }).strength(-8))
                .force("chargeThree", forceIsolate(d3v4.forceManyBody(), function (d) {
                    return d['PUC level'] === '3';
                }).strength(-8))
                .force("x", forceXSeparate)
                .force("y", d3v4.forceY(height / 2).strength(0.1))
                .alphaTarget(0.5)
                .restart()
            labels
                .style("visibility", "visible")
        })

        d3v4.select("#combine").on('click', function () {
            simulation
                .force("charge", null)
                .force("charge", d3v4.forceManyBody().strength(-8))
                .force("x", d3v4.forceX(bubbleSectionWidth / 2).strength(0.1))
                .force("y", d3v4.forceY(height / 2).strength(0.1))
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
                .style('fill', 'black')
                .style('font-size', '16px')
                .style('text-decoration', 'underline')
                .style("font-weight", "bold")
                .text("General Categories")

            unique.forEach(title => {
                slot += 30;
                legend.append('text')
                    .attr("x", bubbleSectionWidth + 20)
                    .attr("y", slot)
                    .style('font-size', '14px')
                    .style('fill', 'black')
                    .style("font-weight", "bold")
                    .text(title)
                legend.append('rect')
                    .attr('width', 12)
                    .attr('height', 12)
                    .attr('fill', bubbleColors.get(title))
                    .attr('x', bubbleSectionWidth + 5)
                    .attr('y', slot - 11)
                    .attr('rx', 2)
                    .attr('ry', 2)
            })
        }

        var node = svg.selectAll("circle")
            .data(data)
            .enter()
            .append("circle")
            .attr('r', function (d) {
                // alert(d)
                return scaleRadius(d[columnForRadius]) + 4
            })
            .style("fill", function (d) {
                return bubbleColors.get(d[columnForColors])
            })
            .attr('class', 'bubble')
            .attr('stroke', '#004d4d')
            .attr('stroke-width', 0)
            .on("mouseover", function (d) {
                d3v4.select(this)
                    .transition()
                    .duration(347)
                    .attr('stroke-width', 1)
                var matrix = this.getBoundingClientRect()
                tooltip.html("PUC level: " + d['PUC level'] + "<br><b>" + d['General category'] + "-</b><br><b>-" + d['Product family'] + "-</b><br><b>-" + d['Product type'] + "</b><br>" + "Product Count: " + d[columnForRadius])
                    .style("left", (matrix.x + matrix.width + 15) + "px")
                    .style("top", (matrix.y + matrix.height - 30) + "px");
                return tooltip.style("visibility", "visible");
            })
            .on("mouseout", function () {
                d3v4.select(this)
                    .transition()
                    .duration(347)
                    .attr('stroke-width', 0)
                return tooltip.style("visibility", "hidden");
            })
            .on("click", function (d) {
                location.href = d['url'];
            });
    }

    return chart;
}

// Level 1 PUCs are at full saturation
// Level 2 PUCs are 50% translucent
// Level 3 PUCs are white
var setOpacity = function(puc_level){
        if (puc_level == 1) {
            return 0.5;
        } else {
            return 1;
        }
}

function nestedBubbleChart(width, height, dataurl, showLegend = true) {
    var color = d3v5.scaleLinear()
    .domain([-1, 4])
    .range(["hsl(152,80%,80%)", "hsl(228,30%,40%)"])
    .interpolate(d3v5.interpolateHcl);

    var sizeScale = d3v5.scaleLinear()
    .range([5,20]);

    pack = data => d3v5.pack()
        .size([width, height])
        .padding(1)
        .radius(d=>sizeScale(d.data["Product count"]))
        (data)
    
    // The chart consumes the csv response from /download_PUCs
    var data = d3v5.csv(dataurl)
        .then(function (data) {
            // Convert the csv to a hierarchy, using guidance from here:
            // https://observablehq.com/@stopyransky/making-hierarchy-from-any-tabular-data

            // Insert an artificial root node to the table
            data.unshift({name:"root", parent:""})

            data.forEach(function(d){
                // add a name value based on which of the three PUC levels is relevant
                d.name = d.name || d["Product type"] || d["Product family"] || d["General category"];
                // Assign a new product_count field to avoid having to quote it
                d.prod_count = parseInt(d["Product count"]);
                // assign a color based on the General Category
                d.color = pucColors.get(d["General category"]);
                // set the opacity
                d.opacity = setOpacity(d["PUC level"]);
                // assign each node's parent node based on what its PUC is
                if (d["Product type"]) {
                        d.parent = d["Product family"];
                    } else if (d["Product family"]) {
                        d.parent = d["General category"];
                    } else if (d["General category"]){
                        d.parent = "root";
                    }
              });

            // stratify the tabular data
              var strat = d3v5.stratify(data)
                .id(function(d) { return d.name; })
                .parentId(function(d) { return d.parent; })
                (data);
            // Call sum and sort on the stratified data
              strat.sum(d => d.prod_count);
              strat.sort((a, b) => b.height - a.height || b.value - a.value) ;
              
            const root = pack(strat)
            let focus = root;
        
        let view;

        const svg = d3v5.select("#nestedcircles")
            .attr("viewBox", `-${width / 2} -${height / 2} ${width} ${height}`)
            .style("display", "block")
            .style("background", "#eae9e0")
            .style("cursor", "pointer")
            .on("click", () => zoom(root));

        const node = svg.append("g")
        .selectAll("circle")
            .data(root.descendants().slice(1))
            .join("circle")
              .attr("class", "bubble")
              .attr("fill", d => d.data["PUC level"] == 3 ? "white" : d.data.color  )
              .attr("opacity", d => d.data.opacity)
              .attr("pointer-events", d => !d.children ? "none" : null)
            .on("mouseover", function() { d3v5.select(this).attr("stroke", "#000"); })
            .on("mouseout", function() { d3v5.select(this).attr("stroke", null); })
            .on("click", d => focus !== d && (zoom(d), d3v5.event.stopPropagation()));
        
        const label = svg.append("g")
           .style("font", "14px sans-serif")
            .attr("pointer-events", "none")
            .attr("text-anchor", "middle")
          .selectAll("text")
            .data(root.descendants())
            .join("text")
                .style("fill-opacity", d => d.parent === root ? 1 : 0)
                .style("display", d => d.parent === root ? "inline" : "none")
                // Display the name with the cumulative count
                .text(d => d.data.name + " (" + d.value + ")");

        zoomTo([root.x, root.y, root.r * 2]);

        function zoomTo(v) {
            const k = width / v[2];
        
            view = v;

            label.attr("transform", d => `translate(${(d.x - v[0]) * k},${(d.y - v[1]) * k})`);
            node.attr("transform", d => `translate(${(d.x - v[0]) * k},${(d.y - v[1]) * k})`);
            node.attr("r", d => d.r * k);
        }

        function zoom(d) {
            const focus0 = focus;
        
            focus = d;
        
            const transition = svg.transition()
                .duration(d3v5.event.altKey ? 7500 : 750)
                .tween("zoom", d => {
                  const i = d3v5.interpolateZoom(view, [focus.x, focus.y, focus.r * 2]);
                  return t => zoomTo(i(t));
                });
        
            label
              .filter(function(d) { return d.parent === focus || this.style.display === "inline"; })
              .transition(transition)
                .style("fill-opacity", d => d.parent === focus ? 1 : 0)
                .on("start", function(d) { if (d.parent === focus) this.style.display = "inline"; })
                .on("end", function(d) { if (d.parent !== focus) this.style.display = "none"; });
          }

        return svg.node();

    }).catch(console.log.bind(console));
}

