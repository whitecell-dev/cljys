# The four commands this repo has. Everything else is a detail of one of them.
# See README.md "Running Things"; `make -n <target>` shows the real command.

.PHONY: probe mutate test counts clean

probe:   # run every probe suite; non-zero if a probe fails or an xfail passes
	@python3 probes/run_probes.py

mutate:  # prove the suite can fail, on a temp copy of the transpiler
	@python3 scripts/mutation_check.py

test:    # transpile and execute test_suite/*.clj; non-gating in CI
	@./run_tests.sh

counts:  # the numbers README quotes, read from the manifest, never hand-counted
	@python3 -c "import json, sys; sys.path.insert(0, 'scripts'); import mutation_check as m; suites = json.load(open('probes/manifest.json'))['suites']; print('%d probes in %d suites: %s' % (sum(len(s['probes']) for s in suites), len(suites), ', '.join('%s %d' % (s['version'], len(s['probes'])) for s in suites))); print('%d mutations: %s' % (len(m.MUTATIONS), ', '.join(x['name'] for x in m.MUTATIONS)))"

clean:   # gitignored output only: run_tests.sh results and bytecode caches
	@rm -rf results __pycache__ probes/__pycache__ scripts/__pycache__