#!/usr/bin/env python
import os
test = "hallo"

match test:
    case "hallo":
        print("hi")
    case "bye":
        print("bye")
    case _:
        print("ka")

print("here")

