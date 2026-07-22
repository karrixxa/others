# Multiplicative Computation in Biological Neural Models — Research Baseline

## Scope and status

- **Status:** approved neuroscience and modeling research baseline for later plan-of-action work.
- **Implementation status:** no runtime change or committed architecture is specified here.
- **Question:** does this project need a biologically distinct “multiplicative neuron,” and which product-like mechanisms are credible candidates for later laboratory comparison?
- **Project verdict:** **OPTIONAL LAB EXPERIMENT — NOT REQUIRED for basic sequence learning.**

## Terminology: no standard “multiplicative neuron” type

There is no distinct, standard biological cell type called a **multiplicative neuron** analogous to a pyramidal, basket, chandelier, or Martinotti cell.

The phrase generally conflates three different claims:

1. **Abstract product or sigma-pi unit:** a computational model that evaluates products or sums of products.
2. **Approximate multiplicative gain:** one variable scales a neuron’s response to another over a bounded operating range, often summarized as \(r(x,c)\approx g(c)f(x)\).
3. **Emergent nonlinear interaction:** voltage-dependent conductance, dendritic subunits, NMDA events, recurrent E/I normalization, neuromodulation, or mixed selectivity generates product-like behavior without exact arithmetic multiplication.

The biologically defensible language for this project is therefore **local nonlinear interaction**, **gain modulation**, or **branch-local coincidence**, not a new neuron class.

## Exact multiplication versus approximate biological interaction

An exact product unit computes a specified algebraic product for all values in its declared domain. Biological evidence instead supports operating-range approximations:

- tuning curves can be scaled approximately while preserving shape;
- synaptic current depends on both conductance and membrane voltage;
- clustered dendritic input can trigger supralinear local events;
- other spatial arrangements can sum sublinearly;
- a population response can be divided by pooled activity;
- a local synaptic eligibility trace can be gated by a delayed modulatory factor.

These mechanisms may be fitted by multiplication or division over limited ranges. That fit does not establish an exact, globally available arithmetic operator. Any exact sigma-pi model should be treated as an abstract control baseline and tested against membrane, spike, locality, and causal-provenance data.

## Biological mechanisms and model equations

### 1. Conductance-based excitation, inhibition, and shunting

\[
C\frac{dV}{dt}
=-g_L(V-E_L)-g_E(t)(V-E_E)-g_I(t)(V-E_I)
\]

with synaptic current:

\[
I_{\mathrm{syn}}(t)=g(t)(E_{\mathrm{rev}}-V)
\]

Conductance and voltage interact multiplicatively in the current equation. Shunting inhibition can strongly affect subthreshold voltage, but it does not automatically produce divisive firing-rate gain; Holt and Koch explicitly found that firing-rate effects can be predominantly subtractive. This is a strong local E/I foundation, not proof of an exact multiplier.

### 2. Dendritic subunits

For branch \(b\):

\[
u_b=\phi\left(\sum_{j\in b}w_{bj}x_j\right)
\]

\[
V_{\mathrm{soma}}\leftarrow
\operatorname{leak}(V_{\mathrm{soma}})
+\sum_b a_bu_b
\]

The nonlinear branch function \(\phi\) can represent threshold-linear, saturating, sigmoid, or plateau behavior. The abstraction treats a pyramidal neuron as a two-layer system: branch-local nonlinear subunits followed by somatic pooling. It is more biologically grounded than unrestricted global products and costs roughly one state per modeled branch.

### 3. NMDA-like voltage gate and coincidence

\[
I_{\mathrm{NMDA}}
=g_Ns(t)B(V)(E_N-V)
\]

\[
B(V)=\frac{1}{1+\alpha e^{-\beta V}}
\]

The voltage-dependent gate makes clustered, coincident input capable of a local NMDA spike or plateau. Experimental support concerns branch-local coincidence and amplification, not exact scalar multiplication. For this project, it is a plausible later L2/3 sensory × context experiment.

### 4. Sigma-pi control model

\[
u=\sum_k w_k\prod_j x_j^{(k)}
\]

Selected product terms are computationally cheap, while unrestricted combinations grow combinatorially. Biological fidelity is low as a direct unit claim; dendritic nonlinearity can approximate selected interactions. A sigma-pi profile is useful only as an explicitly abstract control.

### 5. Bounded gain

\[
I_{\mathrm{eff}}(t)=g_{\mathrm{context}}(t)I_{\mathrm{sensory}}(t)
\]

\[
g_{\mathrm{context}}
=g_{\min}+(g_{\max}-g_{\min})\sigma(u_{\mathrm{context}})
\]

Bounding avoids unrestrained amplification or deterministic zeroing, but bounds alone do not make the mechanism tenant-compliant. Context must arrive over explicit local connections, abstention must not trigger gain, and gain must not guarantee a winner.

### 6. Divisive normalization

\[
r_i=\frac{f(u_i)}
{\sigma+\sum_j a_{ij}f(u_j)}
\]

Normalization is a canonical population computation. A direct global denominator would conflict with strict locality. A biologically stronger project profile would realize the pool through explicit local recurrent/feedforward E/I connectivity and preserve the possibility that every candidate remains silent.

### 7. Synapse-local eligibility × connected modulator

\[
\frac{de_{ij}}{dt}
=F(\mathrm{pre}_i,\mathrm{post}_j)-\frac{e_{ij}}{\tau_e}
\]

\[
\frac{dw_{ij}}{dt}
=\eta M_j(t)e_{ij}(t)
\]

The eligibility trace \(e_{ij}\) belongs to synapse \(i\rightarrow j\). Under strict T9, \(M_j\) must reach the receiving neuron through a defined modulatory connection; a simulator-wide scalar that directly mutates every weight is not equivalent. This product-like interaction is more relevant to local learning than a standalone product neuron.

## Mechanism interpretation

### Conductance and shunting

- **Biology:** direct membrane and synaptic basis.
- **Product-like effect:** voltage-dependent current and possible gain changes.
- **Caution:** shunting does not guarantee divisive firing-rate behavior.
- **Project fit:** strong later foundation for explicit local E/I.

### Dendritic nonlinearities and active subunits

- **Biology:** pyramidal branches support location-dependent sublinear and supralinear integration.
- **Product-like effect:** branch-local conjunctions can approximate selected interaction terms.
- **Project fit:** potentially useful for actual-pattern/context coincidence after local ownership exists.

### NMDA spikes and plateaus

- **Biology:** clustered basal-dendritic input can trigger branch-restricted NMDA spikes and calcium signals.
- **Product-like effect:** sharp coincidence amplification with voltage dependence.
- **Project fit:** strongest first candidate for a local “multiplicative-like” L2/3 laboratory profile.

### Divisive normalization

- **Biology:** broad systems-level evidence supports normalization as a canonical computation.
- **Product-like effect:** response division by pooled activity.
- **Project fit:** later ambiguity/noise control, only through explicit E/I circuitry rather than a global denominator.

### Neuromodulatory or contextual gain

- **Biology:** cortical responses can show approximately multiplicative response gain while preserving tuning shape.
- **Product-like effect:** a context or state variable scales sensory response.
- **Project fit:** possible local L6/apical modulation, but direct evidence for a particular neuromodulator and receptor implementation would be required before claiming a specific biological pathway.

### Mixed selectivity

- **Biology:** nonlinear mixtures of task variables support high-dimensional representations.
- **Product-like effect:** context × sensory interactions appear in response functions without requiring literal product units.
- **Project fit:** useful for ambiguous/contextual patterns after basic representations are causal and learned.

### Three-factor learning

- **Biology/model class:** local pre/post eligibility is gated by a third factor on behavioral timescales.
- **Product-like effect:** eligibility × modulator.
- **Project fit:** the most relevant multiplication-like mechanism for T2/T9 learning, provided all state and delivery remain local.

## Primary and authoritative sources

The DOI URLs below are the approved source set and should be preserved exactly.

1. **Holt, Gary R.; Koch, Christof (1997). “Shunting Inhibition Does Not Have a Divisive Effect on Firing Rates.”**  
   DOI: https://doi.org/10.1162/neco.1997.9.5.1001  
   Supports conductance-based shunting while warning that subthreshold divisive effects do not imply divisive firing-rate gain.

2. **Mel, Bartlett W. (1992). “NMDA-Based Pattern Discrimination in a Modeled Cortical Neuron.”**  
   DOI: https://doi.org/10.1162/neco.1992.4.4.502  
   Supports modeled voltage-dependent NMDA and clustered-synapse mechanisms for sigma-pi-like pattern discrimination.

3. **Schiller, Jackie; Major, Guy; Koester, Helmut J.; Schiller, Yitzhak (2000). “NMDA Spikes in Basal Dendrites of Cortical Pyramidal Neurons.”**  
   DOI: https://doi.org/10.1038/35005094  
   Provides experimental evidence for branch-local NMDA spikes, restricted calcium signals, and coincidence amplification.

4. **Poirazi, Panayiota; Brannon, Terrence; Mel, Bartlett W. (2003). “Pyramidal Neuron as Two-Layer Neural Network.”**  
   DOI: https://doi.org/10.1016/S0896-6273(03)00149-1  
   Supports nonlinear dendritic subunits pooled at the soma.

5. **Poirazi, Panayiota; Brannon, Terrence; Mel, Bartlett W. (2003). “Arithmetic of Subthreshold Synaptic Summation in a Model CA1 Pyramidal Cell.”**  
   DOI: https://doi.org/10.1016/S0896-6273(03)00148-X  
   Supports branch- and location-dependent sublinear/supralinear integration rather than a universal multiplication law.

6. **McAdams, Carrie J.; Maunsell, John H. R. (1999). “Effects of Attention on Orientation-Tuning Functions of Single Neurons in Macaque Cortical Area V4.”**  
   DOI: https://doi.org/10.1523/JNEUROSCI.19-01-00431.1999  
   Supports approximately multiplicative response gain with preserved orientation tuning width in vivo.

7. **Carandini, Matteo; Heeger, David J. (2012). “Normalization as a Canonical Neural Computation.”**  
   DOI: https://doi.org/10.1038/nrn3136  
   Authoritative synthesis of divisive normalization as a circuit/population computation.

8. **Rigotti, Mattia; Barak, Omri; Warden, Melissa R.; Wang, Xiao-Jing; Daw, Nathaniel D.; Miller, Earl K.; Fusi, Stefano (2013). “The Importance of Mixed Selectivity in Complex Cognitive Tasks.”**  
   DOI: https://doi.org/10.1038/nature12160  
   Supports nonlinear mixed selectivity and high-dimensional context-dependent representations.

9. **Frémaux, Nicolas; Gerstner, Wulfram (2016). “Neuromodulated Spike-Timing-Dependent Plasticity, and Theory of Three-Factor Learning Rules.”**  
   DOI: https://doi.org/10.3389/fncir.2015.00085  
   Establishes the eligibility × modulatory-factor model class and synapse-local eligibility requirement.

10. **Gerstner, Wulfram; Lehmann, Marco; Liakoni, Vasiliki; Corneil, Dane; Brea, Johanni (2018). “Eligibility Traces and Plasticity on Behavioral Time Scales: Experimental Support of NeoHebbian Three-Factor Learning Rules.”**  
    DOI: https://doi.org/10.3389/fncir.2018.00053  
    Reviews physiological evidence for eligibility traces and delayed third-factor gating across cortical, striatal, and hippocampal systems.

## Decision matrix

| Mechanism | Biological basis | Tenant alignment | Complexity | Project value and risk |
|---|---|---|---|---|
| Exact sigma-pi products | Abstract model; selected dendritic interactions may approximate terms | Weak unless every factor and weight is neuron-local | Low for selected terms; combinatorial if unrestricted | Control baseline only; high hardcoding/global-factor risk |
| Conductance-based E/I | Strong biophysical basis | Strong for T4/T9 when conductance is receiving-neuron/synapse state | Low–moderate | High foundational value; not itself required for basic sequence |
| Shunting inhibition | Real conductance mechanism; firing-rate division is not guaranteed | Supports local suppression, never winner assignment | Moderate | Useful comparison with explicit caution against “automatic division” claims |
| Dendritic subunits | Strong compartmental-model and physiological basis | Strong for T3/T9 if branch state is neuron-owned | Moderate | High-value optional profile; hard branch thresholds can still force outcomes |
| NMDA spike/plateau | Direct experimental evidence | Strong causal coincidence support when branch-local | Moderate | Best first multiplicative-like candidate; monitor runaway plateaus |
| Divisive normalization | Strong systems/canonical-computation evidence | Compatible only through explicit local E/I connectivity | Moderate–high | Later ambiguity/noise value; global denominator would violate T9 |
| Bounded contextual gain | In-vivo response-gain evidence; pathway specifics remain model-dependent | Compatible when connected, local, and gated by causal state | Low–moderate | Potential L6 value; excessive gain can manufacture threshold crossings |
| Mixed selectivity | Strong in-vivo/computational evidence | Supports context-sensitive representation, not ownership by itself | Moderate | Useful after basic binding; does not solve locality |
| Eligibility × modulator | Strong theoretical and experimental model support | Excellent for T2/T9 if eligibility is synapse-local and modulator connected | Moderate | More relevant to learning than product neurons; global reward mutation is a major risk |

## Project decision

**OPTIONAL LAB EXPERIMENT, NOT REQUIRED for basic sequence learning.**

Basic H1→V1→D0→D1 learning does not require multiplication. Authentic spiking, causal abstention, locally owned recurrent synapses, bounded Hebbian/STDP-style updates, and local prediction readout are sufficient model classes for sequence learning.

Multiplicative computation cannot by itself solve:

- **T3:** a product does not establish neuron-owned one-pattern learning.
- **T6:** a product does not create an emergent one-to-one symbol binding.
- **T9:** global factors, tables, or gain maps remain global even if their arithmetic operation is multiplication.

The most relevant later candidates are:

1. conductance-based local E/I;
2. NMDA-like branch-local coincidence;
3. synapse-local eligibility × a connected modulatory signal.

Exact sigma-pi should remain a control baseline, not the default biological claim.

## Recommended first experiments

Do not combine all mechanisms in one profile. Use paired-seed additive controls.

1. **Conductance E/I versus additive-current control**
   - Replace no causal semantics; change only the local synaptic current model.
   - Measure E/I balance, sparsity, abstention, false winners, and learning.
2. **One NMDA-like dendritic subunit per candidate**
   - Compare additive sensory + context drive against branch-local coincidence.
   - Use actual patterns, not `line_id`, and require authentic somatic spikes.
3. **Synapse-local eligibility × connected modulator**
   - Compare two-factor local STDP with three-factor delayed modulation.
   - Audit the owner and event provenance of every weight delta.
4. **Exact sigma-pi control**
   - Include only selected terms matching the dendritic experiment.
   - Label it abstract and prevent global/catalog factors from entering the product.

## Promotion evidence criteria

A multiplicative profile is eligible for promotion only if:

1. causal abstention invariants already pass;
2. false-winner rate is exactly `0`;
3. learned deltas without causal provenance are exactly `0`;
4. L4 fabrication rate is exactly `0`;
5. refractory violations are `0`;
6. learned state and product/gain factors are demonstrably neuron- or synapse-local;
7. it improves held-out ambiguous/noisy pattern performance over an additive control across paired seeds;
8. the gain is not explained by forced spikes or a reduced willingness to abstain;
9. E/I balance, sparsity, stability, and retention do not regress;
10. performance and binding remain invariant to label, catalog, and neuron order;
11. the added computational cost is reported against the measured benefit;
12. the mechanism’s biological claim matches its evidence: exact product, approximate gain, or nonlinear coincidence are not conflated.

## Safety and anti-hardcoding warning

**Never use deterministic global multiplication or gain to force a winner.**

Unsafe forms include:

- multiplying hardcoded `line_id` and catalog context;
- applying a simulator-wide factor directly to all candidate learning;
- setting a preferred neuron’s gain high enough to guarantee threshold crossing;
- setting all alternatives to zero and calling the survivor a causal winner;
- using multiplication to conceal fixed owner, sequence, or tie-break rules;
- treating inhibitory normalization as permission for another neuron to fire.

After abstention, gain must remain neutral and learning must remain unchanged. A local nonlinear mechanism may alter membrane dynamics; it may not fabricate event truth, ownership, or causal provenance.

## Open research questions

1. Which first experiment has the clearest falsifiable value: conductance E/I, NMDA branch coincidence, or eligibility × modulator?
2. What branch abstraction is the minimum useful model without implying full compartmental fidelity?
3. Which measured operating range justifies calling a response “approximately multiplicative”?
4. Which explicit receptor/pathway evidence would be required before naming a neuromodulatory mechanism?
5. Can local recurrent E/I realize useful normalization without a prohibited global pool?
6. What gain bounds preserve abstention calibration across noisy and novel patterns?
7. How should modulatory timing interact with the event-driven timestep and eligibility decay?
8. What computational budget and effect size justify promotion from lab to biological profile?

## Evidence relationship

Tenant constraints, the forced-win audit, staged causal prerequisites, and benchmark gates are documented in [`../architecture/tenant_compliance_no_forced_win_research.md`](../architecture/tenant_compliance_no_forced_win_research.md). The multiplicative experiments in this document are downstream of those causal-safety requirements.
