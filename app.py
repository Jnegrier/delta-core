import os
import datetime
from dateutil.relativedelta import relativedelta
from logzero import logger
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config.from_object(os.environ["APP_SETTINGS"])
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

from data import crud


@app.route("/")
def main():
    return render_template("index.html")


@app.route("/api/v1/initial_setup", methods=["POST"])
def initial_setup():

    crud.Create.initialise_status_tables()

    data = {"message": "Database initialized successfully"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/status", methods=["GET"])
def get_delta_status():
    logger.info("/api/status")

    data = "Delta Reporter up and running"

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/project", methods=["POST"])
def create_project():
    params = request.get_json(force=True)
    logger.info("/projects/%s", params)

    project_check = crud.Read.project_by_name(params["name"])

    if not project_check:
        project_id = crud.Create.create_project(params["name"])
        message = "New project added successfully"
    else:
        project_id = project_check.id
        message = "Project recovered successfully"

    data = {"message": message, "id": project_id}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/projects", methods=["GET"])
def get_projects():
    logger.info("/get_projects/")
    projects = crud.Read.projects()

    if projects:
        data = []
        for project in projects:
            data.append(
                {
                    "project_id": project.id,
                    "name": project.name,
                    "data": project.data,
                    "project_status": project.project_status.name,
                }
            )
    else:
        data = {"message": "No projects were found"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/project/<int:project_id>", methods=["GET"])
def get_project(project_id):
    logger.info("/project/%i", project_id)

    result = crud.Read.project_by_id(project_id)

    if result:
        data = {
            "project_id": result.id,
            "name": result.name,
            "data": result.data,
            "project_status": result.project_status.name,
        }
    else:
        data = {"message": "No project with the id provided was found"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/launch", methods=["POST"])
def create_launch():
    params = request.get_json(force=True)
    logger.info("/launches/%s", params)

    project_check = crud.Read.project_by_name(params["project"])

    if not project_check:
        project_id = crud.Create.create_project(params["project"])
    else:
        project_id = project_check.id

    launch_id = crud.Create.create_launch(
        params["name"], params.get("data"), project_id
    )

    data = {"message": "New launch added successfully", "id": launch_id}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/finish_launch", methods=["PUT"])
def finish_launch():
    params = request.get_json(force=True)
    logger.info("/update_launch/%s", params)

    failed_runs = crud.Read.test_runs_failed_by_launch_id(params.get("launch_id"))

    if failed_runs:
        launch_id = crud.Update.update_launch(params.get("launch_id"), "Failed")
    else:
        launch_id = crud.Update.update_launch(params.get("launch_id"), "Successful")

    data = {"message": "Launch updated successfully", "id": launch_id}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/launch/<int:launch_id>", methods=["GET"])
def get_launch(launch_id):
    logger.info("/launch/%i", launch_id)

    result = crud.Read.launch_by_id(launch_id)

    if result:
        data = {
            "launch_id": result.id,
            "name": result.name,
            "data": result.data,
            "project": result.project.name,
            "launch_status": result.launch_status.name,
        }
    else:
        data = {"message": "No launch with the id provided was found"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/launch/project/<int:project_id>", methods=["GET"])
def get_launches_by_project_id(project_id):
    logger.info("/launches_by_project_id/%i", project_id)

    result = crud.Read.launch_by_project_id(project_id)

    if result:
        launches = []
        index = -1
        launches_index = {}
        for (
            launch,
            test_run,
            total_count,
            failed_count,
            passed_count,
            running_count,
            incomplete_count,
            skipped_count,
        ) in result:
            if launches == [] or launch.id not in list(launches_index.keys()):
                index = index + 1
                launches_index[launch.id] = index
                launches.append(
                    {
                        "launch_id": launch.id,
                        "project_id": launch.project.id,
                        "name": launch.name,
                        "data": launch.data,
                        "project": launch.project.name,
                        "launch_status": launch.launch_status.name,
                        "test_run_stats": [],
                    }
                )
            launches[launches_index[launch.id]]["test_run_stats"].append(
                {
                    "test_run_id": test_run.id,
                    "test_type": test_run.test_type,
                    "tests_total": total_count if total_count else 0,
                    "tests_failed": failed_count if failed_count else 0,
                    "tests_passed": passed_count if passed_count else 0,
                    "tests_running": running_count if running_count else 0,
                    "tests_incomplete": incomplete_count if incomplete_count else 0,
                    "tests_skipped": skipped_count if skipped_count else 0,
                }
            )
        data = launches
    else:
        data = {"message": "No launch with the project id provided was found"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/test_run", methods=["POST"])
def create_test_run():
    params = request.get_json(force=True)
    logger.info("/create_test_run/%s", params)

    test_run_id = crud.Create.create_test_run(
        params.get("data"),
        params.get("start_datetime"),
        params.get("test_type"),
        params.get("launch_id"),
    )

    data = {"message": "New test run added successfully", "id": test_run_id}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/test_run", methods=["PUT"])
def update_test_run():
    params = request.get_json(force=True)
    logger.info("/update_test_run/%s", params)

    test_run_id = crud.Update.update_test_run(
        params.get("test_run_id"),
        params.get("end_datetime"),
        params.get("data"),
        params.get("test_run_status"),
    )

    data = {"message": "Test run updated successfully", "id": test_run_id}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/test_run/<int:test_run_id>", methods=["GET"])
def get_test_run(test_run_id):
    logger.info("/test_run/%i", test_run_id)

    result = crud.Read.test_run_by_id(test_run_id)

    if result:
        data = {
            "test_run_id": result.id,
            "data": result.data,
            "start_datetime": result.start_datetime,
            "end_datetime": result.end_datetime,
            "duration": diff_dates(result.start_datetime, result.end_datetime),
            "test_type": result.test_type,
            "test_run_status": result.test_run_status.name,
            "launch": result.launch.name,
        }
    else:
        data = {"message": "No test run with the id provided was found"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/test_run/launch/<int:launch_id>", methods=["GET"])
def get_test_runs_by_launch_id(launch_id):
    logger.info("/test_run_by_launch_id/%i", launch_id)

    result = crud.Read.test_run_by_launch_id(launch_id)

    if result:
        test_runs = []
        for (
            test_run,
            total_count,
            failed_count,
            passed_count,
            running_count,
            incomplete_count,
            skipped_count,
        ) in result:
            test_runs.append(
                {
                    "test_run_id": test_run.id,
                    "launch_id": test_run.launch.id,
                    "project_id": test_run.launch.project.id,
                    "data": test_run.data,
                    "start_datetime": test_run.start_datetime,
                    "end_datetime": test_run.end_datetime,
                    "duration": diff_dates(
                        test_run.start_datetime, test_run.end_datetime
                    ),
                    "test_type": test_run.test_type,
                    "test_run_status": test_run.test_run_status.name,
                    "launch_name": test_run.launch.name,
                    "launch_status": test_run.launch.launch_status.name,
                    "tests_total": total_count if total_count else 0,
                    "tests_failed": failed_count if failed_count else 0,
                    "tests_passed": passed_count if passed_count else 0,
                    "tests_running": running_count if running_count else 0,
                    "tests_incomplete": incomplete_count if incomplete_count else 0,
                    "tests_skipped": skipped_count if skipped_count else 0,
                }
            )
        data = test_runs
    else:
        data = {"message": "No launch with the launch id provided was found"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/test_suite", methods=["POST"])
def create_test_suite():
    params = request.get_json(force=True)
    logger.info("/create_test_suite/%s", params)

    project_check = crud.Read.project_by_name(params["project"])

    if not project_check:
        project_id = crud.Create.create_project(params["project"])
    else:
        project_id = project_check.id

    test_suite_check = crud.Read.test_suite_by_name_project_test_type(
        params.get("name"), project_id, params.get("test_type")
    )

    if not test_suite_check:
        test_suite_id = crud.Create.create_test_suite(
            params.get("name"), project_id, None, params.get("test_type")
        )
        message = "New test suite added successfully"
    else:
        test_suite_id = test_suite_check.id
        message = "Test suite is already present"

    data = {"message": message, "test_suite_id": test_suite_id}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/test_suite_history", methods=["POST"])
def create_test_suite_history():
    params = request.get_json(force=True)
    logger.info("/create_test_suite_history/%s", params)

    project_check = crud.Read.project_by_name(params["project"])

    if not project_check:
        project_id = crud.Create.create_project(params["project"])
    else:
        project_id = project_check.id

    test_suite_check = crud.Read.test_suite_by_name_project_test_type(
        params.get("name"), project_id, params.get("test_type")
    )

    if not test_suite_check:
        test_suite_id = crud.Create.create_test_suite(
            params.get("name"), project_id, None, params.get("test_type")
        )
    else:
        test_suite_id = test_suite_check.id

    test_suite_history_id = crud.Create.create_test_suite_history(
        params.get("data"),
        params.get("start_datetime"),
        params.get("test_run_id"),
        test_suite_id,
    )

    data = {
        "message": "New test suite history added successfully",
        "test_suite_history_id": test_suite_history_id,
        "test_suite_id": test_suite_id,
    }

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/test_suite_history", methods=["PUT"])
def update_test_suite_history():
    params = request.get_json(force=True)
    logger.info("/update_test_suite_history/%s", params)

    crud.Update.update_test_suite_history(
        params.get("test_suite_history_id"),
        params.get("end_datetime"),
        params.get("data"),
        params.get("test_suite_status"),
    )

    data = {"message": "Test suite history updated successfully"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/test_suite/<int:test_suite_id>", methods=["GET"])
def get_test_suite(test_suite_id):
    logger.info("/test_suite/%i", test_suite_id)

    result = crud.Read.test_suite_by_id(test_suite_id)

    if result:
        data = {
            "test_suite_id": result.id,
            "name": result.name,
            "data": result.data,
            "test_type": result.test_type,
        }
    else:
        data = {"message": "No test suite with the id provided was found"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/test", methods=["POST"])
def create_test():
    params = request.get_json(force=True)
    logger.info("/create_test/%s", params)

    # TODO(Juan) Check this condition for new tests.
    test_check = crud.Read.test_by_name(params.get("name"))

    if not test_check:
        test_id = crud.Create.create_test(
            params.get("name"), None, params.get("test_suite_id")
        )
        message = "New test added successfully"
    else:
        test_id = test_check.id
        message = "Test is already present"

    data = {"message": message, "test_id": test_id}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/test_history", methods=["POST"])
def create_test_history():
    params = request.get_json(force=True)
    logger.info("/create_test_history/%s", params)

    # TODO(Juan) Check this condition for new tests.
    test_check = crud.Read.test_by_name(params.get("name"))

    if not test_check:
        test_id = crud.Create.create_test(
            params.get("name"), None, params.get("test_suite_id")
        )
    else:
        test_id = test_check.id

    test_history_id = crud.Create.create_test_history(
        params.get("start_datetime"),
        test_id,
        params.get("test_run_id"),
        params.get("test_suite_history_id"),
    )

    data = {
        "message": "New test history added successfully",
        "test_history_id": test_history_id,
        "test_id": test_id,
    }

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/test_history", methods=["PUT"])
def update_test_history():
    params = request.get_json(force=True)
    logger.info("/update_test_history/%s", params)

    crud.Update.update_test_history(
        params.get("test_history_id"),
        params.get("end_datetime"),
        params.get("trace"),
        params.get("file"),
        params.get("message"),
        params.get("error_type"),
        params.get("retries"),
        params.get("test_status"),
    )

    data = {"message": "Test history updated successfully"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/test_history_resolution", methods=["PUT"])
def update_test_history_resolution():
    params = request.get_json(force=True)
    logger.info("/update_test_history_resolution/%s", params)

    crud.Update.update_test_history_resolution(
        params.get("test_history_id"), params.get("test_resolution")
    )

    data = {"message": "Test history resolution updated successfully"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/tests_suite_history/test_run/<int:test_run_id>", methods=["GET"])
def get_tests_suite_history_by_test_run(test_run_id):
    logger.info("/get_tests_suite_history_by_test_run/%i", test_run_id)

    results = crud.Read.test_suite_history_by_test_run(test_run_id)

    if results:
        test_suites_history = []

        for table in results:
            test_suite_history = table[1]
            test_suites_history.append(
                {
                    "test_suite_history_id": test_suite_history.id,
                    "test_suite_id": test_suite_history.test_suite.id,
                    "name": test_suite_history.test_suite.name,
                    "start_datetime": test_suite_history.start_datetime,
                    "end_datetime": test_suite_history.end_datetime,
                    "duration": diff_dates(
                        test_suite_history.start_datetime,
                        test_suite_history.end_datetime,
                    ),
                    "test_suite_status": test_suite_history.test_suite_status.name,
                }
            )
        data = test_suites_history
    else:
        data = {"message": "No tests suites were found"}
    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route(
    "/api/v1/tests_suite_history/test_status/<int:test_suite_status_id>/test_run/<int:test_run_id>",
    methods=["GET"],
)
def get_tests_suite_history_by_test_status_and_test_run_id(
    test_suite_status_id, test_run_id
):
    logger.info(
        "/tests_suite_history/test_status/%i/test_run/%i/",
        test_suite_status_id,
        test_run_id,
    )

    results = crud.Read.test_suite_history_by_test_status_and_test_run_id(
        test_suite_status_id, test_run_id
    )

    if results:
        test_suites_history = []

        for table in results:
            test_suite_history = table[1]
            test_suites_history.append(
                {
                    "test_suite_history_id": test_suite_history.id,
                    "test_suite_id": test_suite_history.test_suite.id,
                    "name": test_suite_history.test_suite.name,
                    "start_datetime": test_suite_history.start_datetime,
                    "end_datetime": test_suite_history.end_datetime,
                    "duration": diff_dates(
                        test_suite_history.start_datetime,
                        test_suite_history.end_datetime,
                    ),
                    "test_suite_status": test_suite_history.test_suite_status.name,
                }
            )
        data = test_suites_history
    else:
        data = {"message": "No tests suites were found"}
    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/tests_history/test_run/<int:test_run_id>", methods=["GET"])
def get_tests_history_by_test_run(test_run_id):
    logger.info("/get_tests_history_by_test_run/%i", test_run_id)

    results = crud.Read.test_history_by_test_run(test_run_id)

    if results:
        test_suites = []
        test_suites_index = {}
        index = -1

        test_run = {
            "test_run_id": results[0][0].id,
            "launch_id": results[0][0].launch.id,
            "project_id": results[0][0].launch.project.id,
            "launch": results[0][0].launch.name,
            "test_type": results[0][0].test_type,
            "start_datetime": results[0][0].start_datetime,
            "end_datetime": results[0][0].end_datetime,
            "duration": diff_dates(
                results[0][0].start_datetime, results[0][0].end_datetime
            ),
            "test_run_status": results[0][0].test_run_status.name,
        }
        for table in results:
            test_suite_history = table[1]
            test_history = table[2]
            total_count = table[3]
            failed_count = table[4]
            passed_count = table[5]
            running_count = table[6]
            incomplete_count = table[7]
            skipped_count = table[8]
            if test_suites == [] or test_suite_history.id not in list(
                test_suites_index.keys()
            ):
                index = index + 1
                test_suites_index[test_suite_history.id] = index
                test_suites.append(
                    {
                        "test_suite_history_id": test_suite_history.id,
                        "test_suite_id": test_suite_history.test_suite.id,
                        "name": test_suite_history.test_suite.name,
                        "start_datetime": test_suite_history.start_datetime,
                        "end_datetime": test_suite_history.end_datetime,
                        "duration": diff_dates(
                            test_suite_history.start_datetime,
                            test_suite_history.end_datetime,
                        ),
                        "test_suite_status": test_suite_history.test_suite_status.name,
                        "tests_total": total_count if total_count else 0,
                        "tests_failed": failed_count if failed_count else 0,
                        "tests_passed": passed_count if passed_count else 0,
                        "tests_running": running_count if running_count else 0,
                        "tests_incomplete": incomplete_count if incomplete_count else 0,
                        "tests_skipped": skipped_count if skipped_count else 0,
                        "tests": [],
                    }
                )
            test_suites[test_suites_index.get(test_suite_history.id)]["tests"].append(
                {
                    "test_history_id": test_history.id,
                    "test_id": test_history.test.id,
                    "name": test_history.test.name,
                    "trace": test_history.trace,
                    "file": test_history.file,
                    "message": test_history.message,
                    "error_type": test_history.error_type,
                    "retries": test_history.retries,
                    "start_datetime": test_history.start_datetime,
                    "end_datetime": test_history.end_datetime,
                    "duration": diff_dates(
                        test_history.start_datetime, test_history.end_datetime
                    ),
                    "status": test_history.test_status.name,
                    "resolution": test_history.test_resolution.name,
                }
            )
        test_run["test_suites"] = test_suites
        data = [test_run]
    else:
        data = {"message": "No tests were found"}
    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/test/<int:test_id>", methods=["GET"])
def get_test_by_test_id(test_id):
    logger.info("/test/%i", test_id)

    result = crud.Read.test_by_id(test_id)

    if result:
        data = {
            "test_id": result.id,
            "name": result.name,
            "data": result.data,
            "test_suite_id": result.test_suite_id,
        }
    else:
        data = {"message": "No test with the id provided was found"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route(
    "/api/v1/tests_history/test_status/<int:test_status_id>/test_run/<int:test_run_id>",
    methods=["GET"],
)
def get_tests_history_by_test_status_and_test_run_id(test_status_id, test_run_id):
    logger.info(
        "/tests_history/test_status/%i/test_run/%i/", test_status_id, test_run_id
    )

    tests_history = crud.Read.test_history_by_test_status_and_test_run_id(
        test_status_id=test_status_id, test_run_id=test_run_id
    )

    if tests_history:
        data = []
        for test_history in tests_history:
            data.append(
                {
                    "test_history_id": test_history.id,
                    "name": test_history.test.name,
                    "start_datetime": test_history.start_datetime,
                    "end_datetime": test_history.end_datetime,
                    "duration": diff_dates(
                        test_history.start_datetime, test_history.end_datetime
                    ),
                    "test_status": test_history.test_status.name,
                    "test_resolution": test_history.test_resolution.name,
                    "trace": test_history.trace,
                    "file": test_history.file,
                    "message": test_history.message,
                    "error_type": test_history.error_type,
                    "retries": test_history.retries,
                }
            )
    else:
        data = {"message": "No tests were found"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/tests_history/test_status/<int:test_status_id>", methods=["GET"])
def get_tests_history_by_test_status_id(test_status_id):
    logger.info("/tests_history_by_test_status_id/%i", test_status_id)

    tests_history = crud.Read.test_history_by_test_status_id(test_status_id)

    if tests_history:
        data = []
        for test_history in tests_history:
            data.append(
                {
                    "test_history_id": test_history.id,
                    "name": test_history.test.name,
                    "start_datetime": test_history.start_datetime,
                    "end_datetime": test_history.end_datetime,
                    "duration": diff_dates(
                        test_history.start_datetime, test_history.end_datetime
                    ),
                    "test_status": test_history.test_status.name,
                    "test_resolution": test_history.test_resolution.name,
                }
            )
    else:
        data = {"message": "No tests were found"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route(
    "/api/v1/tests_history/test_resolution/<int:test_resolution_id>", methods=["GET"]
)
def get_tests_history_by_test_resolution_id(test_resolution_id):
    logger.info("/tests_history_by_test_resolution_id/%i", test_resolution_id)

    tests_history = crud.Read.test_history_by_test_resolution_id(test_resolution_id)

    if tests_history:
        data = []
        for test_history in tests_history:
            data.append(
                {
                    "test_history_id": test_history.id,
                    "name": test_history.test.name,
                    "start_datetime": test_history.start_datetime,
                    "end_datetime": test_history.end_datetime,
                    "duration": diff_dates(
                        test_history.start_datetime, test_history.end_datetime
                    ),
                    "test_status": test_history.test_status.name,
                    "test_resolution": test_history.test_resolution.name,
                }
            )
    else:
        data = {"message": "No tests were found"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.route("/api/v1/tests_history/test_suite/<int:test_suite_id>", methods=["GET"])
def get_tests_history_by_test_suite_id(test_suite_id):
    logger.info("/tests_history_by_test_suite_id/%i", test_suite_id)

    results = crud.Read.test_history_by_test_suite_id(test_suite_id)

    if results:
        data = []
        for table in results:
            test_history = table[0]
            test = table[1]
            test_suite = table[2]
            data.append(
                {
                    "test_history_id": test_history.id,
                    "name": test.name,
                    "start_datetime": test_history.start_datetime,
                    "end_datetime": test_history.end_datetime,
                    "duration": diff_dates(
                        test_history.start_datetime, test_history.end_datetime
                    ),
                    "test_status": test_history.test_status.name,
                    "test_resolution": test_history.test_resolution.name,
                    "test_suite": test_suite.name,
                    "test_type": test_suite.name,
                }
            )
    else:
        data = {"message": "No tests were found"}

    resp = jsonify(data)
    resp.status_code = 200

    return resp


@app.errorhandler(404)
def notfound(error):
    data = {"message": "The endpoint requested was not found"}

    resp = jsonify(data)
    resp.status_code = 404

    return resp


def diff_dates(date1, date2):
    if not date1:
        return None
    if not date2:
        date2 = datetime.datetime.now()

    diff = relativedelta(date2, date1)

    return {
        "years": diff.years,
        "months": diff.months,
        "days": diff.days,
        "hours": diff.hours,
        "minutes": diff.minutes,
        "seconds": diff.seconds,
        "microseconds": diff.microseconds,
    }


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=os.getenv("PORT", 5000))
