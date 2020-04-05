import argparse
import os
import CO2Meter
import time
import slackweb
from tinydb import TinyDB
from datetime import datetime

file_name = "../room_condition.json"


def measure_room_condition():
    SENSOR_READ_INTERVAL = 2  # [sec]

    db = TinyDB(file_name)
    sensor = CO2Meter.CO2Meter("/dev/hidraw0")

    while True:
        time.sleep(SENSOR_READ_INTERVAL)
        room_condition = sensor.get_data()
        is_ready = all(key in room_condition for key in ("co2", "temperature"))
        if is_ready:
            break

        print(room_condition)
        print("Retry...")

    now = int(datetime.now().timestamp())
    db.insert({"time": now, "room_condition": room_condition})


def notify_room_condition_to_slack():
    db = TinyDB(file_name)
    if len(db.all()) == 0:
        return

    last_condition = db.all()[-1]
    last_condition_time = datetime.fromtimestamp(last_condition["time"])
    last_condition_co2 = last_condition["room_condition"]["co2"]
    last_condition_temperature = last_condition["room_condition"]["temperature"]

    slack = slackweb.Slack(url=os.environ["SLACK_WEBHOOK_URL"])

    notify_text = "```Time: {}\nCO2: {} ppm\nTemperature: {} ℃```".format(
        last_condition_time, last_condition_co2, last_condition_temperature)
    slack.notify(text=notify_text)


def alert_room_condition_to_slack():
    CO2_ALERT_THRESHOLD = 1000  # [ppm]

    db = TinyDB(file_name)
    if len(db.all()) == 0:
        return

    last_condition = db.all()[-1]
    last_condition_co2 = last_condition["room_condition"]["co2"]

    if CO2_ALERT_THRESHOLD <= last_condition_co2:
        slack = slackweb.Slack(url=os.environ["SLACK_WEBHOOK_URL"])
        alert_text = "<!channel> :warning: そろそろ換気をしましょう。[ CO2: {} ppm ]".format(
            last_condition_co2)
        slack.notify(text=alert_text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("type")
    args = parser.parse_args()

    if args.type == "measure":
        measure_room_condition()
    elif args.type == "notify":
        notify_room_condition_to_slack()
    elif args.type == "alert":
        alert_room_condition_to_slack()
