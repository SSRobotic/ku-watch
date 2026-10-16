"""Use relative include paths to stay below Windows subprocess length limits."""
Import("env")
import os
def shorten(build_env):
    base = build_env.subst('$PROJECT_DIR')
    paths = []
    for entry in build_env.get('CPPPATH', []):
        value = build_env.subst(str(entry))
        if os.path.isabs(value):
            try:
                value = os.path.relpath(value, base)
            except ValueError:
                pass
        paths.append(value.replace('\\', '/'))
    build_env.Replace(CPPPATH=paths)

if os.name == 'nt':
    shorten(env)
    def middleware(build_env, node):
        shorten(build_env)
        return node
    env.AddBuildMiddleware(middleware, '*')
