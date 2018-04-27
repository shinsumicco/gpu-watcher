// Wrapping in nv.addGraph allows for '0 timeout render', stores rendered charts in nv.graphs, and may do more in the future... it's NOT required
var chart = {};
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
        update_graph(gpu_status_data["data"]);
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
                values_m.push({x: data[hostname][gpu_index]["time_stamp"][i] * 1000, y: 100 * data[hostname][gpu_index]["memory_used"][i]/data[hostname][gpu_index]["memory_total"][i]});
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

        var y_label = monitor_type=="util"?"GPU Utilization (%)":"Memory Consumption (%)";
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

function update_graph(data){
    for (hostname in data){
        for (gpu_index in data[hostname]){
            chart_data[hostname]["util"][gpu_index].values.shift();
            chart_data[hostname]["util"][gpu_index].values.push(
                {
                    x: data[hostname][gpu_index]["time_stamp"] * 1000,
                    y: data[hostname][gpu_index]["utilization_gpu"]
                }
            );

            chart_data[hostname]["memory"][gpu_index].values.shift();
            chart_data[hostname]["memory"][gpu_index].values.push(
                {
                    x: data[hostname][gpu_index]["time_stamp"] * 1000,
                    y: 100 * data[hostname][gpu_index]["memory_used"] / data[hostname][gpu_index]["memory_total"]
                }
            );
        }
        chart[hostname]["util"].update();
        chart[hostname]["memory"].update();
    }
}