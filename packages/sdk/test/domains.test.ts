import assert from "node:assert/strict";
import test from "node:test";

import {
  applicationDomains,
  domains,
  coordinationDomains,
  isApplicationDomain,
  isProofDomain,
  proofDomains,
} from "../dist/domains.js";

test("protocol-v3 application, proof, and coordination hash domains stay separated", () => {
  const application = Object.values(applicationDomains);
  const proof = Object.values(proofDomains);
  assert.equal(application.length, 7);
  assert.equal(application.some((domain) => proof.includes(domain)), false);
  assert.equal(proof.length, 6);
  for (const domain of application) {
    assert.equal(isApplicationDomain(domain), true);
    assert.equal(isProofDomain(domain), false);
  }
  for (const domain of proof) {
    assert.equal(isProofDomain(domain), true);
    assert.equal(isApplicationDomain(domain), false);
  }
  assert.deepEqual(domains, { ...applicationDomains, ...proofDomains });
  assert.deepEqual(coordinationDomains, {
    STATEMENT: "PQTC.V3.STATEMENT",
    PROOF: "PQTC.V3.PROOF",
    CHECKPOINT: "PQTC.V3.CHECKPOINT",
    VERIFICATION: "PQTC.V3.VERIFICATION",
  });
  assert.equal(Object.isFrozen(applicationDomains), true);
  assert.equal(Object.isFrozen(proofDomains), true);
  assert.equal(Object.isFrozen(coordinationDomains), true);
  assert.equal(Object.isFrozen(domains), true);
});
