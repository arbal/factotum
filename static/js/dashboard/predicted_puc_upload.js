
$(function() {


  // We can attach the `fileselect` event to all file inputs on the page
  $(document).on('change', ':file', function() {
    var input = $(this),
        numFiles = input.get(0).files ? input.get(0).files.length : 1,
        label = input.val().replace(/\\/g, '/').replace(/.*\//, '');
    input.trigger('fileselect', [numFiles, label]);
  });

  // We can watch for our custom `fileselect` event like this
  $(document).ready( function() {
    $('#progress').hide()

      $(':file').on('fileselect', function(event, numFiles, label) {

          var input = $(this).parents('.input-group').find(':text'),
              log = numFiles > 1 ? numFiles + ' files selected' : label;

          if( input.length ) {
              input.val(log);
          } else {
              if( log ) alert(log);
          }

      });
  });
///////
    // pull task status every 1/2 second
    var taskSchedule = setInterval(() => setTaskState(), 500);

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

        async function deleteTask(task_id) {
            if (task_id) {
                await fetch(`/api/tasks/${task_id}/`, {
                    method: "DELETE",
                    headers: { "X-CSRFToken": Cookies.get("csrftoken") }
                }).then(res => console.log(res.ok));
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

        if (task_id) {
            $('#progress').show()
            var task = await getTask(task_id);
            if (task) {
                if (taskDone(task)) {
                    // task done, clear the pull interval
                    clearInterval(taskSchedule);
                    // delete this task
                    await deleteTask(task_id);
                    // hide the spinner
                   $('#progress').hide()
                   $("#task_status").text(task.result[0] + " PUC assignments added, " + task.result[1] + " updated." );
                }
            }
        } else {
         //   window.location.href = redict_to;
        }
    }

});

