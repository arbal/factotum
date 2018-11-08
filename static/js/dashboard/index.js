nv.addGraph(function () {
    var chart = nv.models.lineChart(x_is_date=true)
        .color(d3.scale.category10().range())
        .x(function(d) {return d3.time.format("%Y-%m-%d").parse(d['x']);});
    chart.xAxis
        .axisLabel('Date')
        .tickFormat(function(d) {
            return d3.time.format('%m/%d/%y')(new Date(d))
        });
    chart.xScale(d3.time.scale());
    chart.yAxis
        .tickFormat(d3.format(',.0f'));
    d3.select('#datadocument_count_by_date_lineChart svg')
        .datum(datadocument_count_by_date)
        .transition().duration(500)
        .attr('height', 350)
        .call(chart);
    return chart;
});


nv.addGraph(function() {
    var chart = nv.models.discreteBarChart()
        // .color(d3.scale.category10().range());
        .color(['#0071bc']);
    chart.yAxis.tickFormat(d3.format(',.0f'));
    chart.x(function(d) { return d.label })
        .y(function(d) { return d.value });

    d3.select('#datadocument_count_by_month_barchart svg')
        .datum(datadocument_count_by_month)
        .call(chart);

    nv.utils.windowResize(chart.update);

    return chart;
});

nv.addGraph(function() {
    var chart = nv.models.discreteBarChart()
        .color(['#0071bc']);
    chart.yAxis.tickFormat(d3.format(',.0f'));
    chart.x(function(d) { return d.label })
        .y(function(d) { return d.value });

    d3.select('#product_with_puc_count_by_month_barchart svg')
        .datum(product_with_puc_count_by_month)
        .call(chart);

    nv.utils.windowResize(chart.update);

    return chart;
});
