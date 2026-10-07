/**
 * Mounts a page's stylesheet for as long as that page is mounted.
 *
 * Every HR Django template carries its `<style>` block inside
 * `{% block content %}`, so the rules only exist while that page is on
 * screen. Reproducing that here keeps one template's `.stats` / `.tbl` rules
 * from leaking into the next page, exactly like the server-rendered originals.
 */
export function PageStyle({ css }: { css: string }) {
  return <style dangerouslySetInnerHTML={{ __html: css }} />
}
