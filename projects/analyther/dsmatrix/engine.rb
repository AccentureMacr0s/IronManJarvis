require_relative "mirror"
require_relative "rules"

class DSMatrix
  def self.score(tokens, pattern)
    pattern_tokens = pattern.split(" ")
    return 0.0 if pattern_tokens.empty?

    common = (tokens & pattern_tokens).size
    common.to_f / pattern_tokens.size
  end

  def self.analyze(text)
    tokens = Mirror.normalize(text)

    RULES.map do |name, pattern|
      { name: name, score: score(tokens, pattern) }
    end.sort_by { |row| -row[:score] }
  end
end
