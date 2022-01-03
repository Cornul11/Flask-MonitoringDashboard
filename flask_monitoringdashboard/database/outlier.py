from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from flask_monitoringdashboard.database import Outlier, Request


def add_outlier(session, request_id, cpu_percent, memory, stacktrace, request):
    """
    Adds an Outlier object in the database.
    :param session: session for the database
    :param request_id: id of the request
    :param cpu_percent: cpu load of the server when processing the request
    :param memory: memory load of the server when processing the request
    :param stacktrace: stack trace of the request
    :param request: triple containing the headers, environment and url
    """
    headers, environ, url = request
    outlier = Outlier(
        request_id=request_id,
        request_header=headers,
        request_environment=environ,
        request_url=url,
        cpu_percent=cpu_percent,
        memory=memory,
        stacktrace=stacktrace,
    )
    if getattr(Outlier, "is_mongo_db", False):
        outlier.endpoint_id = Request().get_collection(session).find_one({
            "id": request_id
        })["endpoint_id"]
        outlier.get_collection(session).insert_one(outlier)
    else:
        session.add(outlier)


def get_outliers_sorted(session, endpoint_id, offset, per_page):
    """
    Gets a list of Outlier objects for a certain endpoint, sorted by most recent request time
    :param session: session for the database
    :param endpoint_id: id of the endpoint for filtering the requests
    :param offset: number of items to skip
    :param per_page: number of items to return
    :return list of Outlier objects of a specific endpoint
    """
    if getattr(Outlier, "is_mongo_db", False):
        requests = list(Request().get_collection(session).find({
            "endpoint_id": endpoint_id
        }).sort([("time_requested", 1)]))
        outliers = dict()
        for elem in Outlier().get_collection(session).find({"endpoint_id": endpoint_id}).skip(int(offset)).limit(
                int(per_page)):
            outliers.setdefault(elem["request_id"], []).append(Outlier(**elem))
        results = []
        for request in requests:
            if outliers.get(request["id"]):
                for current_outlier in outliers[request["id"]]:
                    current_outlier["request"] = Request(**request)
                results.extend(outliers[request["id"]])
            if len(results) > int(per_page):
                break
        return results
    else:
        result = (
            session.query(Outlier)
            .join(Outlier.request)
            .options(joinedload(Outlier.request).joinedload(Request.endpoint))
            .filter(Request.endpoint_id == endpoint_id)
            .order_by(desc(Request.time_requested))
            .offset(offset)
            .limit(per_page)
            .all()
        )
        session.expunge_all()
        return result


def get_outliers_cpus(session, endpoint_id):
    """
    Gets list of CPU loads of all outliers of a certain endpoint
    :param session: session for the database
    :param endpoint_id: id of the endpoint
    :return list of cpu percentages as strings
    """
    if getattr(Outlier, "is_mongo_db", False):
        return list(elem.get("cpu_percent") for elem in
                    Outlier().get_collection(session).find({"endpoint_id": endpoint_id}))
    else:
        outliers = (
            session.query(Outlier.cpu_percent)
            .join(Outlier.request)
            .filter(Request.endpoint_id == endpoint_id)
            .all()
        )
        return [outlier[0] for outlier in outliers]
