// Corrente de ferro entre a lateral e a área de trabalho: o desenho é o fundo
// do bloco (backgrounds/chain.png); este mod só ocupa o espaço, transparente.
import { View, div } from "gpui-kit";
export default class Chain extends View {
  render() { return div().size_full(); }
}
