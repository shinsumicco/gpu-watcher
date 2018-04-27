// Wrapping in nv.addGraph allows for '0 timeout render', stores rendered charts in nv.graphs, and may do more in the future... it's NOT required
var chart = {};
var data;
var chart_data = {};

// last 2 are dummy (for now)
var color_set = ["#00ff00", "#ff007f", "#ffa500", "#ffa500"];

var socket = new WebSocket('ws://localhost:8000/gpu_status');
socket.onopen = function(event){
    console.log("connected");
}
socket.onclose = function(){
    console.log("disconnected");
}
socket.onmessage = function(event){
    var gpu_status_data =JSON.parse(event.data);
    if (gpu_status_data["status"] == "initial"){
        draw_initial(gpu_status_data["data"]);
    }else if (gpu_status_data["status"] == "latest"){
        console.log("received latest data");
    }
}

function draw_initial(data){
    for (hostname in data){
        chart_data[hostname] = {
            "util": [],
            "memory": []
        };
        chart[hostname] = {};

        for (gpu_index in data[hostname]){
            var values_u = [];
            var values_m = [];
            for (var i = 0; i < data[hostname][gpu_index]["time_stamp"].length; i++){
                values_u.push({x: data[hostname][gpu_index]["time_stamp"][i] * 1000, y: data[hostname][gpu_index]["utilization_gpu"][i]});
                values_m.push({x: data[hostname][gpu_index]["time_stamp"][i] * 1000, y: data[hostname][gpu_index]["utilization_memory"][i]});
            }

            chart_data[hostname]["util"].push(
                {
                    values: values_u,
                    key: data[hostname][gpu_index]["gpu_name"] + "(" + gpu_index + ")",
                    color: color_set[gpu_index]
                }
            );

            chart_data[hostname]["memory"].push(
                {
                    values: values_u,
                    key: data[hostname][gpu_index]["gpu_name"] + "(" + gpu_index + ")",
                    color: color_set[gpu_index]
                }
            );
        }

        init_graph(hostname, "util");
        init_graph(hostname, "memory");
    }
}

function init_graph(hostname, monitor_type){
    nv.addGraph(function() {
        var c = nv.models.lineChart();
        c.useInteractiveGuideline(true);
        c.forceY([0, 100]);

        c.xAxis.axisLabel("Time");
        c.xAxis.tickFormat(function(d) {
            return d3.time.format("%b %e %X")(new Date(d));
        }).showMaxMin(false);
        c.xAxis.rotateLabels(-10);

        var y_label = monitor_type=="util"?"GPU Utilization (%)":"Memory Utilization (%)";
        c.yAxis.axisLabel(y_label);
        c.yAxis.tickFormat(d3.format('d'));

        d3.select("#" + hostname).select("." + monitor_type).append('svg')
        .datum(chart_data[hostname][monitor_type])
        .call(c);

        nv.utils.windowResize(c.update);

        chart[hostname][monitor_type] = c;
        return c;
    });
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
