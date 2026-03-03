#!/usr/bin/env python3
import aws_cdk as cdk
from capacity_reservation_notifier.capacity_reservation_notifier_stack import CapacityReservationNotifierStack
from cdk_nag import AwsSolutionsChecks
from aws_cdk import Aspects

app = cdk.App()
CapacityReservationNotifierStack(app, "CapacityReservationNotifierStack")

Aspects.of(app).add(AwsSolutionsChecks())
app.synth()
