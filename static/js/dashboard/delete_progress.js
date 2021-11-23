$(document).ready(function () {
    // pull task status every 10 seconds
    var taskSchedule = setInterval(() => setTaskState(), 10000);

    async function setTaskState() {
        async function getJSON(url) {
            return await fetch(url).then(res => res.json());
        }

        async function getTask(task_id) {
            // retrieve the task
            if (task_id) {
                var task_status = await getJSON(`/api/tasks/${task_id}/`);
                return task_status[task_id];
            } else {
                return null;
            }
        }

        function taskDone(task) {
            // task considered done when success or fail
            return ["SUCCESS", "FAILURE"].includes(
                task.status
            );
        }

        // Set task status
        var task_id = $('#task_id').val();
        var redict_to = $("#redirect_to").val();
        if (task_id) {
            var task = await getTask(task_id);
            if (task) {
                $("#task_status").text(task.status);
                console.log(task.status);

                if (taskDone(task)) {
                    // task done, clear the pull interval
                    clearInterval(taskSchedule);
                    // direct to the originated url
                    window.location.href = redict_to;
                }
            }
        } else {
            window.location.href = redict_to;
        }
    }
});