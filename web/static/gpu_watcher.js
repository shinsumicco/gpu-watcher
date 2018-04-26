// Wrapping in nv.addGraph allows for '0 timeout render', stores rendered charts in nv.graphs, and may do more in the future... it's NOT required
var chart;
var data;
var chart_data = {};

var socket = new WebSocket('ws://localhost:8000/gpu_status');
socket.onopen = function(event){
    console.log("connected");
}
socket.onclose = function(){
    console.log("disconnected");
}
socket.onmessage = function(event){
    var gpu_status_data =JSON.parse(event.data);
    // add the data to the graph, here.
    for (hostname in gpu_status_data){
        console.log("gpu data received:");
        if (data[0].values.length == 240){
            data[0].values.shift();
        }
        if (data[1].values.length == 240){
            data[1].values.shift();
        }
        data[0].values.push({x: data[0].values.length, y: gpu_status_data[hostname]["1"]["u"]});
        data[1].values.push({x: data[1].values.length, y: gpu_status_data[hostname]["2"]["u"]});
        chart.update();
    }
}

var init = function(){
    nv.addGraph(function() {
        chart = nv.models.lineChart()
        .options({
            duration: 300,
            useInteractiveGuideline: true
        })
        ;
        // chart sub-models (ie. xAxis, yAxis, etc) when accessed directly, return themselves, not the parent chart, so need to chain separately
        chart.xAxis
        .axisLabel("Time (s)")
        .tickFormat(d3.format(',.1f'))
        .staggerLabels(true)
        ;
        chart.yAxis
        .axisLabel('Voltage (v)')
        .tickFormat(function(d) {
            if (d == null) {
                return 'N/A';
            }
            return d3.format(',.2f')(d);
        })
        ;
        data = sinAndCos();
        d3.select('#chart1').append('svg')
        .datum(data)
        .call(chart);
        nv.utils.windowResize(chart.update);
        return chart;
    });
}

function sinAndCos() {
    var sin = [],
    sin2 = [],
    cos = [],
    rand = [],
    rand2 = []
    ;
    for (var i = 0; i < 100; i++) {
        sin.push({x: i, y: i % 10 == 5 ? null : Math.sin(i/10) }); //the nulls are to show how defined works
        cos.push({x: i, y: .5 * Math.cos(i/10)});
    }
    return [
    {
        area: true,
        values: sin,
        key: "Sine Wave",
        color: "#ff7f0e",
        strokeWidth: 4,
        classed: 'dashed'
    },
    {
        values: cos,
        key: "Cosine Wave",
        color: "#2ca02c"
    }
    ];
}
