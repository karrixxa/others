"""Explicit, timestep-local dendritic compartments for coincidence cells.

These classes are deliberately independent of ``Neuron.receive_input``.  A
compartment records only physical deliveries made during one engine timestep;
it has no eligibility trace and cannot retain charge into a later timestep.
"""

from dataclasses import dataclass
from enum import Enum


class DendriteRole(str, Enum):
    BASAL = "basal"
    APICAL = "apical"


@dataclass(frozen=True)
class DendriticDelivery:
    source: str
    step: int
    signal: float
    weight: float
    charge: float


class DendriteCompartment:
    """One explicitly addressed, non-integrating dendritic compartment."""

    def __init__(self, role: DendriteRole):
        self.role = DendriteRole(role)
        self.delivery_step = None
        self.deliveries = []

    def deliver(self, source: str, signal: float, weight: float, step: int):
        if self.delivery_step is not None and self.delivery_step != step:
            raise RuntimeError("compartment state must be cleared between timesteps")
        self.delivery_step = int(step)
        charge = float(signal) * float(weight)
        event = DendriticDelivery(source, int(step), float(signal), float(weight), charge)
        self.deliveries.append(event)
        return event

    @property
    def active(self):
        return any(event.signal > 0.0 for event in self.deliveries)

    @property
    def charge(self):
        return sum(event.charge for event in self.deliveries)

    def clear(self):
        self.delivery_step = None
        self.deliveries.clear()


@dataclass
class DendriticConnection:
    """A connection whose target is an explicit compartment, never a soma."""

    source: str
    target: DendriteCompartment
    weight: float
    plastic: bool = False

    def deliver(self, signal: float, step: int):
        return self.target.deliver(self.source, signal, self.weight, step)


class CoincidencePyramidalCell:
    """Two physical compartments gating charge onto an ordinary neuron soma.

    Basal or apical delivery alone never reaches ``soma``.  When both roles
    receive a physical event at the same engine step, their delivered charge is
    evaluated against ``coincidence_threshold``.  The caller may then update
    plastic apical weights, but the firing decision has already used the
    pre-learning delivery weights.
    """

    def __init__(self, soma, basal_source, apical_sources, basal_weight,
                 apical_weights, coincidence_threshold):
        self.soma = soma
        self.basal = DendriteCompartment(DendriteRole.BASAL)
        self.apical = DendriteCompartment(DendriteRole.APICAL)
        self.basal_connection = DendriticConnection(
            basal_source, self.basal, float(basal_weight), plastic=False)
        self.apical_connections = [
            DendriticConnection(source, self.apical, float(weight), plastic=True)
            for source, weight in zip(apical_sources, apical_weights)
        ]
        self.coincidence_threshold = float(coincidence_threshold)
        self.last_coincidence_step = None
        self.last_d_before_learning = None
        self.last_basal_sources = ()
        self.last_apical_sources = ()
        self.last_basal_charge = 0.0
        self.last_apical_charge = 0.0

    @property
    def decoder_weights(self):
        return [connection.weight for connection in self.apical_connections]

    @property
    def potential(self):
        return self.soma.potential

    @potential.setter
    def potential(self, value):
        self.soma.potential = value

    @property
    def threshold(self):
        return self.soma.threshold

    @property
    def refractory_timer(self):
        return self.soma.refractory_timer

    def deliver_basal(self, signal, step):
        if signal > 0.0:
            self.basal_connection.deliver(signal, step)

    def deliver_apical(self, source_index, signal, step):
        if signal > 0.0:
            self.apical_connections[source_index].deliver(signal, step)

    def resolve_coincidence(self, step):
        self.last_basal_sources = tuple(event.source for event in self.basal.deliveries)
        self.last_apical_sources = tuple(event.source for event in self.apical.deliveries)
        self.last_basal_charge = float(self.basal.charge)
        self.last_apical_charge = float(self.apical.charge)
        same_step = (self.basal.active and self.apical.active
                     and self.basal.delivery_step == step
                     and self.apical.delivery_step == step)
        if not same_step:
            return False
        self.last_coincidence_step = int(step)
        self.last_d_before_learning = self.apical.charge
        if self.basal.charge + self.last_d_before_learning < self.coincidence_threshold:
            return False
        # Compartment charge reaches the soma only through a qualifying
        # coincidence.  Deposit exactly one threshold unit so the ordinary
        # soma owns threshold/reset/refractory and axonal firing semantics.
        if self.soma.refractory_timer <= 0:
            self.soma.potential += self.soma.threshold
        return self.soma.check_threshold()

    def fire(self):
        return self.soma.fire()

    def check_threshold(self):
        return self.soma.check_threshold()

    def clear_compartments(self):
        self.basal.clear()
        self.apical.clear()

    def update(self, dt=1):
        self.soma.update()
        self.clear_compartments()

    def __getstate__(self):
        return self.__dict__.copy()

    def __setstate__(self, state):
        self.__dict__.update(state)

    def __getattr__(self, name):
        return getattr(self.soma, name)
